"""ETF 数据查询服务 - 从 etf schema 下的各个表查询数据"""
from typing import Any
from sqlalchemy import text
from sqlmodel import Session


class EtfService:
    """ETF 数据查询服务"""

    @staticmethod
    def get_etf_basic_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        keyword: str | None = None,
        exchange: str | None = None,
        list_status: str | None = None,
        etf_type: str | None = None,
        mgr_name: str | None = None,
        index_codes: list[str] | None = None,
        ts_codes: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取 ETF 基础信息列表
        从 etf.etf_basic 表查询
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        where: list[str] = ["TRUE"]
        if keyword:
            params["kw"] = f"%{keyword}%"
            where.append("(ts_code ILIKE :kw OR csname ILIKE :kw OR extname ILIKE :kw OR index_name ILIKE :kw OR index_code ILIKE :kw)")
        if exchange:
            params["exchange"] = exchange
            where.append("exchange = :exchange")
        if list_status:
            params["list_status"] = list_status
            where.append("list_status = :list_status")
        if etf_type:
            params["etf_type"] = etf_type
            where.append("etf_type = :etf_type")
        if mgr_name:
            params["mgr_name"] = mgr_name
            where.append("mgr_name = :mgr_name")
        if index_codes:
            codes = [c.strip() for c in index_codes if c and c.strip()]
            if codes:
                if len(codes) == 1:
                    where.append("index_code = :index_code")
                    params["index_code"] = codes[0]
                else:
                    placeholders = []
                    for i, code in enumerate(codes):
                        key = f"index_code_{i}"
                        placeholders.append(f":{key}")
                        params[key] = code
                    where.append(f"index_code IN ({', '.join(placeholders)})")
        if ts_codes:
            codes = [c.strip() for c in ts_codes if c and c.strip()]
            if codes:
                if len(codes) == 1:
                    where.append("ts_code = :ts_code")
                    params["ts_code"] = codes[0]
                else:
                    placeholders = []
                    for i, code in enumerate(codes):
                        key = f"ts_code_{i}"
                        placeholders.append(f":{key}")
                        params[key] = code
                    where.append(f"ts_code IN ({', '.join(placeholders)})")
        where_sql = " AND ".join(where)
        sql_count = text(f"""
            SELECT COUNT(*) AS total
            FROM etf.etf_basic
            WHERE {where_sql}
        """)
        total = int(session.execute(sql_count, params).scalar() or 0)
        sql_data = text(f"""
            SELECT 
                ts_code, csname, extname, cname, index_code, index_name,
                setup_date::text as setup_date, list_date::text as list_date,
                list_status, exchange, mgr_name, custod_name, mgt_fee,
                etf_type, update_time::text as update_time, create_time::text as create_time
            FROM etf.etf_basic
            WHERE {where_sql}
            ORDER BY ts_code
            OFFSET :skip LIMIT :limit
        """)
        rows = session.execute(sql_data, params)
        items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
        return items, total

