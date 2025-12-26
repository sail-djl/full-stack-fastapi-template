"""债券数据查询和同步服务 - 从 bond schema 下的各个表查询和同步数据"""
import logging
import traceback
from typing import Any, Optional

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


def _quote_identifier(name: str) -> str:
    return f'"{name}"'


def _to_yyyymmdd(d: str | Any) -> str:
    if not d:
        return d
    if isinstance(d, str):
        if '-' in d:
            return d.replace('-', '')
        return d
    from datetime import date
    if isinstance(d, date):
        return d.strftime("%Y%m%d")
    return str(d)


def _ensure_schema(session: Session) -> None:
    try:
        session.exec(text("CREATE SCHEMA IF NOT EXISTS bond"))
        session.commit()
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        session.rollback()


def _upsert_records(session: Session, table: str, records: list[dict], primary_keys: list[str]) -> tuple[int, int]:
    if not records:
        return 0, 0
    
    first_keys = list(records[0].keys())
    keys = [k for k in first_keys if k not in ['id', 'update_time', 'create_time']]
    
    if not all(pk in keys for pk in primary_keys):
        missing_keys = [pk for pk in primary_keys if pk not in keys]
        logger.error(f"Upsert failed: Missing primary keys {missing_keys}")
        return 0, len(records)

    quoted_cols = ", ".join([_quote_identifier(k) for k in keys])
    vals = ", ".join([f":{k}" for k in keys])
    
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
    except Exception as e:
        logger.error(f"批量插入失败，表: {table}: {e}\n{traceback.format_exc()}")
        session.rollback()
        for idx, r in enumerate(records):
            try:
                session.execute(text(sql_str), r)
                session.commit()
                success += 1
            except Exception as e2:
                logger.error(f"单条插入失败，表: {table}，第 {idx+1} 条: {e2}")
                session.rollback()
                failed += 1
                
    return success, failed


class BondService:
    """债券数据服务"""

    @staticmethod
    def get_bond_list(
        session: Session,
        table: str,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] = None,
        order_by: str = None,
    ) -> dict[str, Any]:
        _ensure_schema(session)
        
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = {}
        
        if filters:
            for key, value in filters.items():
                if value is not None and value != '':
                    if key in ['start_date', 'end_date']:
                        if key == 'start_date':
                            query += f" AND trade_date >= :start_date"
                            params["start_date"] = value
                        elif key == 'end_date':
                            query += f" AND trade_date <= :end_date"
                            params["end_date"] = value
                    elif key in ['trade_date', 'ann_date']:
                        query += f" AND {key} = :{key}"
                        params[key] = value
                    else:
                        query += f" AND {_quote_identifier(key)} = :{key}"
                        params[key] = value
        
        if order_by:
            query += f" ORDER BY {order_by}"
        else:
            if 'trade_date' in table:
                query += " ORDER BY trade_date DESC"
            elif 'ann_date' in table:
                query += " ORDER BY ann_date DESC"
            elif 'list_date' in table:
                query += " ORDER BY list_date DESC"
        
        query += " LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        try:
            result = session.execute(text(query), params)
            items = []
            for row in result:
                row_dict = dict(row._mapping)
                row_dict.pop('id', None)
                items.append(row_dict)
                
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
                        elif key in ['trade_date', 'ann_date']:
                            count_query += f" AND {key} = :{key}"
                            count_params[key] = value
                        else:
                            count_query += f" AND {_quote_identifier(key)} = :{key}"
                            count_params[key] = value
            
            total = session.execute(text(count_query), count_params).scalar()
            
            return {"data": items, "count": total}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Query failed for {table}: {error_msg}\n{traceback.format_exc()}")
            error_lower = error_msg.lower()
            if 'does not exist' in error_lower or 'relation' in error_lower or 'table' in error_lower:
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
        if not settings.TUSHARE_TOKEN:
            raise ValueError("Tushare token not configured")
        
        try:
            import tushare as ts
            import pandas as pd
        except ImportError as e:
            raise ValueError("Tushare or pandas not installed")

        _ensure_schema(session)

        pro = ts.pro_api(settings.TUSHARE_TOKEN)
        if settings.TUSHARE_API_URL:
            pro._DataApi__http_url = settings.TUSHARE_API_URL
        
        processed_params = {}
        for key, value in params.items():
            if value and isinstance(value, str) and ('start_date' in key or 'end_date' in key or 'trade_date' in key or 'list_date' in key or 'ann_date' in key):
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
                return {"message": "No data found", "success": 0, "failed": 0}
            
            df = df.where(pd.notnull(df), None)
            
            if date_columns:
                from datetime import date
                for date_col in date_columns:
                    if date_col in df.columns:
                        try:
                            def validate_and_convert_date(value):
                                if pd.isna(value) or value is None:
                                    return None
                                str_value = str(value).strip()
                                if len(str_value) != 8:
                                    return None
                                if not str_value.isdigit():
                                    return None
                                year = int(str_value[:4])
                                if year < 1900 or year > 2100:
                                    return None
                                try:
                                    parsed_date = pd.to_datetime(str_value, format='%Y%m%d', errors='coerce')
                                    if pd.isna(parsed_date):
                                        return None
                                    return parsed_date.date()
                                except Exception:
                                    return None
                            
                            df[date_col] = df[date_col].apply(validate_and_convert_date)
                        except Exception as e:
                            logger.error(f"日期字段 {date_col} 格式转换失败: {e}")
                            raise
            
            records = df.to_dict("records")
            
            if field_mapping:
                for record in records:
                    for tushare_field, db_field in field_mapping.items():
                        if tushare_field in record:
                            record[db_field] = record.pop(tushare_field)
            
            success, failed = _upsert_records(session, table, records, primary_keys)
            logger.info(f"数据同步完成，表: {table}，成功: {success}，失败: {failed}")
            
            return {"message": "Sync complete", "success": success, "failed": failed}
            
        except Exception as e:
            logger.error(f"同步 {tushare_api} 到表 {table} 失败: {e}\n{traceback.format_exc()}")
            raise ValueError(f"Sync failed: {e}")

