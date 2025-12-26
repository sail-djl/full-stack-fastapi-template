"""宏观经济数据查询和同步服务 - 从 macro schema 下的各个表查询和同步数据"""
import logging
import traceback
from typing import Any, Optional
from datetime import date

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


def _quote_identifier(name: str) -> str:
    """为标识符添加双引号转义（PostgreSQL 需要）"""
    return f'"{name}"'


def _to_yyyymmdd(d: date) -> str:
    """将 date 对象转换为 YYYYMMDD 格式字符串"""
    return d.strftime("%Y%m%d")


def _parse_iso_date(s: str) -> date:
    """解析 ISO 格式日期字符串 (YYYY-MM-DD) 为 date 对象"""
    try:
        return date.fromisoformat(s)
    except ValueError:
        # 尝试解析 YYYYMMDD 格式
        if len(s) == 8:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        raise


def _ensure_schema(session: Session) -> None:
    """确保macro schema存在"""
    try:
        session.exec(text("CREATE SCHEMA IF NOT EXISTS macro"))
        session.commit()
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        session.rollback()


def _upsert_records(session: Session, table: str, records: list[dict], primary_keys: list[str]) -> tuple[int, int]:
    """通用upsert函数，用于批量插入或更新记录"""
    if not records:
        return 0, 0
    
    first_keys = list(records[0].keys())
    logger.info(f"Upsert记录字段: {first_keys}")
    # 过滤掉系统字段
    keys = [k for k in first_keys if k not in ['id', 'update_time', 'create_time']]
    logger.info(f"Upsert使用字段: {keys}，主键要求: {primary_keys}")
    
    if not all(pk in keys for pk in primary_keys):
        missing_keys = [pk for pk in primary_keys if pk not in keys]
        logger.error(f"Upsert failed: Missing primary keys {missing_keys}，可用字段: {keys}")
        return 0, len(records)

    # 构建SQL（为字段名添加双引号转义，避免与保留关键字冲突）
    quoted_cols = ", ".join([_quote_identifier(k) for k in keys])
    vals = ", ".join([f":{k}" for k in keys])
    
    # Update set (排除主键)
    update_cols = [k for k in keys if k not in primary_keys]
    if update_cols:
        update_set = ", ".join([f"{_quote_identifier(k)} = EXCLUDED.{_quote_identifier(k)}" for k in update_cols])
        quoted_primary_keys = ", ".join([_quote_identifier(pk) for pk in primary_keys])
        sql_str = f"""
            INSERT INTO {table} ({quoted_cols})
            VALUES ({vals})
            ON CONFLICT ({quoted_primary_keys})
            DO UPDATE SET
                {update_set},
                update_time = CURRENT_TIMESTAMP
        """
    else:
        quoted_primary_keys = ", ".join([_quote_identifier(pk) for pk in primary_keys])
        sql_str = f"""
            INSERT INTO {table} ({quoted_cols})
            VALUES ({vals})
            ON CONFLICT ({quoted_primary_keys})
            DO NOTHING
        """
    
    success = 0
    failed = 0
    
    try:
        session.execute(text(sql_str), records)
        session.commit()
        success = len(records)
        logger.debug(f"批量插入成功，表: {table}，记录数: {success}")
    except Exception as e:
        logger.error(f"批量插入失败，表: {table}，记录数: {len(records)}: {e}\n{traceback.format_exc()}")
        session.rollback()
        # 重试，逐条插入
        logger.info(f"开始逐条插入，表: {table}，记录数: {len(records)}")
        for idx, r in enumerate(records):
            try:
                session.execute(text(sql_str), r)
                session.commit()
                success += 1
            except Exception as e2:
                logger.error(f"单条插入失败，表: {table}，第 {idx+1} 条记录: {e2}，记录内容: {r}\n{traceback.format_exc()}")
                session.rollback()
                failed += 1
                
    return success, failed


class MacroService:
    """宏观经济数据服务"""

    @staticmethod
    def get_macro_list(
        session: Session,
        table: str,
        skip: int = 0,
        limit: int = 100,
        date_col: str = "date",
        date_filter: Optional[str] = None,
        start_param: Optional[str] = None,
        end_param: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        通用查询方法，用于查询宏观经济数据列表
        
        Args:
            session: 数据库会话
            table: 表名（如 "macro.gdp"）
            skip: 跳过的记录数
            limit: 返回的记录数
            date_col: 日期字段名（如 "date", "month", "quarter"）
            date_filter: 精确日期过滤
            start_param: 开始日期/月份/季度
            end_param: 结束日期/月份/季度
            
        Returns:
            包含data和count的字典
        """
        _ensure_schema(session)
        
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = {}
        
        if date_filter:
            query += f" AND {date_col} = :date_filter"
            params["date_filter"] = date_filter
        if start_param:
            query += f" AND {date_col} >= :start_param"
            params["start_param"] = start_param
        if end_param:
            query += f" AND {date_col} <= :end_param"
            params["end_param"] = end_param
            
        query += f" ORDER BY {date_col} DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        try:
            result = session.execute(text(query), params)
            items = []
            for row in result:
                row_dict = dict(row._mapping)
                # 移除系统字段用于返回
                row_dict.pop('id', None)
                items.append(row_dict)
                
            # 获取总数
            count_query = f"SELECT COUNT(*) FROM {table} WHERE 1=1"
            count_params = {}
            if date_filter:
                count_query += f" AND {date_col} = :date_filter"
                count_params["date_filter"] = date_filter
            if start_param:
                count_query += f" AND {date_col} >= :start_param"
                count_params["start_param"] = start_param
            if end_param:
                count_query += f" AND {date_col} <= :end_param"
                count_params["end_param"] = end_param
                
            total = session.execute(text(count_query), count_params).scalar()
            
            return {"data": items, "count": total}
        except Exception as e:
            logger.error(f"Query failed for {table}: {e}")
            return {"data": [], "count": 0}

    @staticmethod
    def sync_from_tushare(
        session: Session,
        table: str,
        primary_keys: list[str],
        tushare_api: str,
        params: dict[str, Any],
        date_column: Optional[str] = None,
        field_mapping: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        通用同步方法，从Tushare同步数据
        
        Args:
            session: 数据库会话
            table: 表名（如 "macro.gdp"）
            primary_keys: 主键列表（如 ["quarter"] 或 ["date"]）
            tushare_api: Tushare API方法名（如 "cn_gdp"）
            params: Tushare API参数（可能包含需要转换的日期参数）
            date_column: 日期字段名（如果需要在同步时转换日期格式，如 "date"）
            
        Returns:
            包含message, success, failed的字典
        """
        if not settings.TUSHARE_TOKEN:
            logger.error("Tushare token 未配置")
            raise ValueError("Tushare token not configured")
        
        try:
            import tushare as ts
            import pandas as pd
        except ImportError as e:
            logger.error(f"导入 tushare 或 pandas 失败: {e}")
            raise ValueError("Tushare or pandas not installed")

        _ensure_schema(session)

        pro = ts.pro_api(settings.TUSHARE_TOKEN)
        if settings.TUSHARE_API_URL:
            pro._DataApi__http_url = settings.TUSHARE_API_URL
        
        # 处理日期参数转换（如果参数中包含日期且需要转换为YYYYMMDD格式）
        processed_params = {}
        for key, value in params.items():
            if value and isinstance(value, str) and ('start_date' in key or 'end_date' in key):
                # 如果是日期参数且包含'-'，转换为YYYYMMDD格式
                if '-' in value:
                    try:
                        date_obj = _parse_iso_date(value)
                        processed_params[key] = _to_yyyymmdd(date_obj)
                    except Exception as e:
                        logger.warning(f"Failed to parse date parameter {key}={value}: {e}")
                        processed_params[key] = value
                else:
                    processed_params[key] = value
            else:
                processed_params[key] = value
        
        try:
            logger.info(f"开始同步 {tushare_api}，表: {table}，参数: {processed_params}")
            df = getattr(pro, tushare_api)(**processed_params)
            
            if df is None or df.empty:
                logger.warning(f"Tushare API {tushare_api} 返回空数据，参数: {processed_params}")
                return {"message": "No data found", "success": 0, "failed": 0}
            
            logger.info(f"Tushare API {tushare_api} 返回 {len(df)} 条记录")
            logger.info(f"DataFrame 列名: {df.columns.tolist()}")
            
            try:
                df = df.where(pd.notnull(df), None)
            except Exception as e:
                logger.error(f"处理 DataFrame 空值失败: {e}\n{traceback.format_exc()}")
                raise
            
            # 如果指定了date_column，转换日期格式（YYYYMMDD -> DATE）
            if date_column and date_column in df.columns:
                try:
                    df[date_column] = pd.to_datetime(df[date_column], format='%Y%m%d').dt.date
                    logger.info(f"日期字段 {date_column} 格式转换完成")
                except Exception as e:
                    logger.error(f"日期字段 {date_column} 格式转换失败: {e}\n{traceback.format_exc()}")
                    raise
            
            try:
                records = df.to_dict("records")
                logger.info(f"数据转换完成，共 {len(records)} 条记录")
                
                # 记录原始字段名
                if records:
                    logger.info(f"原始字段名: {list(records[0].keys())}")
                
                # 如果字段名都是大写，自动转换为小写（适用于 PMI 等表）
                # 检查是否有大写字段名（排除系统字段）
                data_fields = [k for k in records[0].keys() if k not in ['ID', 'CREATE_TIME', 'UPDATE_TIME', 'CREATE_BY', 'UPDATE_BY']]
                if records and data_fields and all(k.isupper() for k in data_fields):
                    logger.info(f"检测到字段名全为大写，自动转换为小写")
                    for record in records:
                        # 创建新的字典，将字段名转换为小写
                        new_record = {}
                        for key, value in record.items():
                            if key in ['ID', 'CREATE_TIME', 'UPDATE_TIME', 'CREATE_BY', 'UPDATE_BY']:
                                # 系统字段跳过（不会写入数据库）
                                continue
                            new_record[key.lower()] = value
                        record.clear()
                        record.update(new_record)
                    if records:
                        logger.info(f"转换后第一条记录的字段: {list(records[0].keys())}")
                
                # 字段名映射（将 Tushare 字段名映射到数据库字段名）
                if field_mapping:
                    logger.info(f"应用字段名映射: {field_mapping}")
                    for idx, record in enumerate(records):
                        for tushare_field, db_field in field_mapping.items():
                            if tushare_field in record:
                                record[db_field] = record.pop(tushare_field)
                                logger.debug(f"记录 {idx}: 字段 '{tushare_field}' 映射为 '{db_field}'")
                    # 验证映射结果
                    if records:
                        logger.info(f"映射后第一条记录的字段: {list(records[0].keys())}")
                else:
                    logger.info(f"未提供字段映射，使用原始字段名。记录字段: {list(records[0].keys()) if records else '无记录'}")
            except Exception as e:
                logger.error(f"DataFrame 转字典失败: {e}\n{traceback.format_exc()}")
                raise
            
            try:
                success, failed = _upsert_records(session, table, records, primary_keys)
                logger.info(f"数据同步完成，表: {table}，成功: {success}，失败: {failed}")
            except Exception as e:
                logger.error(f"数据写入数据库失败，表: {table}: {e}\n{traceback.format_exc()}")
                raise
            
            return {"message": "Sync complete", "success": success, "failed": failed}
            
        except Exception as e:
            logger.error(f"同步 {tushare_api} 到表 {table} 失败: {e}\n{traceback.format_exc()}")
            raise ValueError(f"Sync failed: {e}")

