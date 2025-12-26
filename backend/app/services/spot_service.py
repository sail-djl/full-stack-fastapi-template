"""现货数据查询和同步服务 - 从 spot schema 下的各个表查询和同步数据"""
import logging
import traceback
from typing import Any, Optional

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


def _quote_identifier(name: str) -> str:
    """为标识符添加双引号转义（PostgreSQL 需要）"""
    return f'"{name}"'


def _to_yyyymmdd(d: str | Any) -> str:
    """将 YYYY-MM-DD 格式日期转换为 YYYYMMDD 格式字符串"""
    if not d:
        return d
    if isinstance(d, str):
        if '-' in d:
            return d.replace('-', '')
        return d
    # 如果是date对象，转换为YYYYMMDD
    from datetime import date
    if isinstance(d, date):
        return d.strftime("%Y%m%d")
    return str(d)


def _parse_iso_date(s: str):
    """解析 ISO 格式日期字符串 (YYYY-MM-DD) 为 date 对象"""
    from datetime import date
    try:
        return date.fromisoformat(s)
    except ValueError:
        # 尝试解析 YYYYMMDD 格式
        if len(s) == 8:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        raise


def _ensure_schema(session: Session) -> None:
    """确保spot schema存在"""
    try:
        session.exec(text("CREATE SCHEMA IF NOT EXISTS spot"))
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


class SpotService:
    """现货数据服务"""

    @staticmethod
    def get_spot_list(
        session: Session,
        table: str,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] = None,
        order_by: str = None,
    ) -> dict[str, Any]:
        """
        通用查询方法，用于查询现货数据列表
        
        Args:
            session: 数据库会话
            table: 表名（如 "spot.sge_basic"）
            skip: 跳过的记录数
            limit: 返回的记录数
            filters: 过滤条件字典
            order_by: 排序字段（如 "trade_date DESC"）
            
        Returns:
            包含data和count的字典
        """
        _ensure_schema(session)
        
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = {}
        
        if filters:
            for key, value in filters.items():
                if value is not None and value != '':
                    if key in ['start_date', 'end_date']:
                        # 日期范围查询（针对trade_date字段）
                        if key == 'start_date':
                            query += f" AND trade_date >= :start_date"
                            params["start_date"] = value
                        elif key == 'end_date':
                            query += f" AND trade_date <= :end_date"
                            params["end_date"] = value
                    elif key == 'trade_date':
                        query += f" AND trade_date = :trade_date"
                        params["trade_date"] = value
                    else:
                        # 其他字段使用精确匹配
                        query += f" AND {_quote_identifier(key)} = :{key}"
                        params[key] = value
        
        if order_by:
            query += f" ORDER BY {order_by}"
        else:
            # 默认排序
            if 'trade_date' in table:
                query += " ORDER BY trade_date DESC"
            elif 'list_date' in table:
                query += " ORDER BY list_date DESC"
        
        query += " LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        try:
            logger.info(f"Executing query: {query}")
            logger.info(f"Query params: {params}")
            result = session.execute(text(query), params)
            items = []
            for row in result:
                row_dict = dict(row._mapping)
                # 移除系统字段用于返回
                row_dict.pop('id', None)
                items.append(row_dict)
            
            logger.info(f"Query returned {len(items)} items")
                
            # 获取总数
            count_query = f"SELECT COUNT(*) FROM {table} WHERE 1=1"
            count_params = {}
            if filters:
                for key, value in filters.items():
                    if value is not None and value != '':
                        if key in ['start_date', 'end_date']:
                            if key == 'start_date':
                                count_query += f" AND trade_date >= :start_date"
                                count_params["start_date"] = value
                            elif key == 'end_date':
                                count_query += f" AND trade_date <= :end_date"
                                count_params["end_date"] = value
                        elif key == 'trade_date':
                            count_query += f" AND trade_date = :trade_date"
                            count_params["trade_date"] = value
                        else:
                            count_query += f" AND {_quote_identifier(key)} = :{key}"
                            count_params[key] = value
            
            logger.info(f"Executing count query: {count_query}")
            logger.info(f"Count params: {count_params}")
            total = session.execute(text(count_query), count_params).scalar()
            logger.info(f"Total count: {total}")
            
            return {"data": items, "count": total}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query failed for {table}: {error_msg}\n{traceback.format_exc()}")
            # 检查是否是表不存在
            error_lower = error_msg.lower()
            if 'does not exist' in error_lower or 'relation' in error_lower or 'table' in error_lower:
                logger.error(f"Table {table} does not exist. Please create the table first by running the SQL scripts in 2-库表/8-现货/")
                return {
                    "data": [], 
                    "count": 0,
                    "error": f"Table {table} does not exist. Please create the table first."
                }
            return {"data": [], "count": 0}

    @staticmethod
    def sync_from_tushare(
        session: Session,
        table: str,
        primary_keys: list[str],
        tushare_api: str,
        params: dict[str, Any],
        date_columns: Optional[list[str]] = None,
        field_mapping: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        通用同步方法，从Tushare同步数据
        
        Args:
            session: 数据库会话
            table: 表名（如 "spot.sge_basic"）
            primary_keys: 主键列表（如 ["ts_code"] 或 ["ts_code", "trade_date"]）
            tushare_api: Tushare API方法名（如 "sge_basic"）
            params: Tushare API参数（可能包含需要转换的日期参数）
            date_columns: 需要转换的日期字段列表（如 ["list_date", "trade_date"]）
            field_mapping: 字段名映射字典（Tushare字段名 -> 数据库字段名）
            
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
            if value and isinstance(value, str) and ('start_date' in key or 'end_date' in key or 'trade_date' in key or 'list_date' in key):
                # 如果是日期参数且包含'-'，转换为YYYYMMDD格式
                if '-' in value:
                    processed_params[key] = _to_yyyymmdd(value)
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
            
            # 如果指定了date_columns，转换日期格式（YYYYMMDD -> DATE）
            if date_columns:
                from datetime import date
                for date_col in date_columns:
                    if date_col in df.columns:
                        try:
                            # 先检查并清理异常日期值
                            def validate_and_convert_date(value):
                                """验证并转换日期值，无效值返回None"""
                                if pd.isna(value) or value is None:
                                    return None
                                
                                # 转换为字符串进行检查
                                str_value = str(value).strip()
                                
                                # 检查长度是否为8位（YYYYMMDD格式）
                                if len(str_value) != 8:
                                    logger.debug(f"日期值长度异常: {str_value} (长度: {len(str_value)})")
                                    return None
                                
                                # 检查是否为纯数字
                                if not str_value.isdigit():
                                    logger.debug(f"日期值包含非数字字符: {str_value}")
                                    return None
                                
                                # 检查年份是否在合理范围内（1900-2100）
                                year = int(str_value[:4])
                                if year < 1900 or year > 2100:
                                    logger.debug(f"日期年份超出合理范围: {str_value} (年份: {year})")
                                    return None
                                
                                # 尝试解析日期
                                try:
                                    parsed_date = pd.to_datetime(str_value, format='%Y%m%d', errors='coerce')
                                    if pd.isna(parsed_date):
                                        logger.debug(f"日期解析失败: {str_value}")
                                        return None
                                    return parsed_date.date()
                                except Exception as e:
                                    logger.debug(f"日期解析异常: {str_value}, 错误: {e}")
                                    return None
                            
                            # 应用验证和转换
                            df[date_col] = df[date_col].apply(validate_and_convert_date)
                            
                            # 统计转换结果
                            valid_count = df[date_col].notna().sum()
                            total_count = len(df)
                            invalid_count = total_count - valid_count
                            
                            if invalid_count > 0:
                                logger.warning(f"日期字段 {date_col} 转换完成，有效: {valid_count}, 无效: {invalid_count}")
                            else:
                                logger.info(f"日期字段 {date_col} 格式转换完成，共 {valid_count} 条有效记录")
                        except Exception as e:
                            logger.error(f"日期字段 {date_col} 格式转换失败: {e}\n{traceback.format_exc()}")
                            raise
            
            try:
                records = df.to_dict("records")
                logger.info(f"数据转换完成，共 {len(records)} 条记录")
                
                # 记录原始字段名
                if records:
                    logger.info(f"原始字段名: {list(records[0].keys())}")
                
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

