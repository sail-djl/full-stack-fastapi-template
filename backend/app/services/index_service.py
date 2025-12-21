"""指数数据查询服务 - 从 index schema 下的各个表查询数据"""
from typing import Any
from datetime import timedelta, date
from sqlalchemy import text
from sqlmodel import Session


class IndexService:
    """指数数据查询服务"""

    @staticmethod
    def get_index_basic_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        keyword: str | None = None,
        market: str | None = None,
        publisher: str | None = None,
        category: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取指数基础信息列表
        从 index.index_basic 表查询
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        where: list[str] = ["TRUE"]
        
        if keyword:
            params["kw"] = f"%{keyword}%"
            where.append("(ts_code ILIKE :kw OR name ILIKE :kw OR fullname ILIKE :kw OR publisher ILIKE :kw)")
        if market:
            params["market"] = market
            where.append("market = :market")
        if publisher:
            params["publisher"] = publisher
            where.append("publisher ILIKE :publisher")
        if category:
            params["category"] = category
            where.append("category ILIKE :category")
            
        where_sql = " AND ".join(where)
        
        sql_count = text(f"""
            SELECT COUNT(*) AS total
            FROM index.index_basic
            WHERE {where_sql}
        """)
        total = int(session.execute(sql_count, params).scalar() or 0)
        
        sql_data = text(f"""
            SELECT 
                ts_code,
                name,
                fullname,
                market,
                publisher,
                index_type,
                category,
                base_date::text as base_date,
                base_point,
                list_date::text as list_date,
                exp_date::text as exp_date,
                weight_rule,
                desc_text,
                update_time::text as update_time,
                create_time::text as create_time
            FROM index.index_basic
            WHERE {where_sql}
            ORDER BY ts_code
            OFFSET :skip LIMIT :limit
        """)
        rows = session.execute(sql_data, params)
        items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
        return items, total

    @staticmethod
    def get_index_daily_list(
        session: Session,
        ts_code: str | list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        获取指数日线行情列表
        从 index.index_daily 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        where: list[str] = ["TRUE"]
        params: dict[str, Any] = {"limit": limit}

        if ts_code:
            # 支持字符串（单个或逗号分隔）、列表
            if isinstance(ts_code, str):
                # 如果是逗号分隔的字符串，转换为列表
                codes = [c.strip() for c in ts_code.split(',') if c.strip()]
            else:
                codes = ts_code
            
            if codes:
                if len(codes) == 1:
                    where.append("ts_code = :ts_code")
                    params["ts_code"] = codes[0]
                else:
                    # 使用 IN 语法，为每个代码创建参数
                    placeholders = []
                    for i, code in enumerate(codes):
                        key = f"ts_code_{i}"
                        placeholders.append(f":{key}")
                        params[key] = code
                    where.append(f"ts_code IN ({', '.join(placeholders)})")
        if start_date:
            where.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where)
        
        sql = text(f"""
            SELECT 
                ts_code,
                trade_date::text as trade_date,
                close, open, high, low, pre_close,
                change, pct_chg, vol, amount
            FROM index.index_daily
            WHERE {where_sql}
            ORDER BY trade_date DESC
            LIMIT :limit
        """)
        
        rows = session.execute(sql, params)
        items: list[dict[str, Any]] = []
        for row in rows:
            r = dict(row._mapping)
            # 确保数值字段是 float
            for k, v in r.items():
                if k not in ['ts_code', 'trade_date'] and v is not None:
                    try:
                        r[k] = float(v)
                    except (ValueError, TypeError):
                        pass
            items.append(r)
            
        return items

    @staticmethod
    def get_index_dailybasic_list(
        session: Session,
        ts_code: str | list[str] | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        获取大盘指数每日指标列表
        从 index.index_dailybasic 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        where: list[str] = ["TRUE"]
        params: dict[str, Any] = {"limit": limit}

        if ts_code:
            # 支持字符串（单个或逗号分隔）、列表
            if isinstance(ts_code, str):
                codes = [c.strip() for c in ts_code.split(',') if c.strip()]
            else:
                codes = ts_code
            
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
        if trade_date:
            where.append("trade_date = :trade_date")
            params["trade_date"] = trade_date
        if start_date:
            where.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where)
        
        sql = text(f"""
            SELECT 
                ts_code,
                trade_date::text as trade_date,
                total_mv, float_mv, total_share, float_share, free_share,
                turnover_rate, turnover_rate_f, pe, pe_ttm, pb
            FROM index.index_dailybasic
            WHERE {where_sql}
            ORDER BY trade_date DESC
            LIMIT :limit
        """)
        
        rows = session.execute(sql, params)
        items: list[dict[str, Any]] = []
        for row in rows:
            r = dict(row._mapping)
            # 确保数值字段是 float
            for k, v in r.items():
                if k not in ['ts_code', 'trade_date'] and v is not None:
                    try:
                        r[k] = float(v)
                    except (ValueError, TypeError):
                        pass
            items.append(r)
            
        return items

    @staticmethod
    def get_index_weekly_list(
        session: Session,
        ts_code: str | list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        获取指数周线行情列表
        从 index.index_weekly 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        where: list[str] = ["TRUE"]
        params: dict[str, Any] = {"limit": limit}

        if ts_code:
            # 支持字符串（单个或逗号分隔）、列表
            if isinstance(ts_code, str):
                codes = [c.strip() for c in ts_code.split(',') if c.strip()]
            else:
                codes = ts_code
            
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
        if start_date:
            where.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where)
        
        sql = text(f"""
            SELECT 
                ts_code,
                trade_date::text as trade_date,
                close, open, high, low, pre_close,
                change, pct_chg, vol, amount
            FROM index.index_weekly
            WHERE {where_sql}
            ORDER BY trade_date DESC
            LIMIT :limit
        """)
        
        rows = session.execute(sql, params)
        items: list[dict[str, Any]] = []
        for row in rows:
            r = dict(row._mapping)
            for k, v in r.items():
                if k not in ['ts_code', 'trade_date'] and v is not None:
                    try:
                        r[k] = float(v)
                    except (ValueError, TypeError):
                        pass
            items.append(r)
            
        return items

    @staticmethod
    def get_index_classify_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        index_code: str | None = None,
        level: str | None = None,
        parent_code: str | None = None,
        src: str = "SW2021",
        keyword: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取申万行业分类列表
        从 index.index_classify 表查询
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit, "src": src}
        where: list[str] = ["src = :src"]
        
        if keyword:
            params["kw"] = f"%{keyword}%"
            where.append("(index_code ILIKE :kw OR industry_code ILIKE :kw OR industry_name ILIKE :kw)")
        
        if index_code:
            where.append("index_code = :index_code")
            params["index_code"] = index_code
        
        if level:
            where.append("level = :level")
            params["level"] = level
        
        if parent_code is not None:
            where.append("parent_code = :parent_code")
            params["parent_code"] = parent_code
            
        where_sql = " AND ".join(where)
        
        sql_count = text(f"""
            SELECT COUNT(*) AS total
            FROM index.index_classify
            WHERE {where_sql}
        """)
        total = int(session.execute(sql_count, params).scalar() or 0)
        
        sql_data = text(f"""
            SELECT 
                index_code,
                industry_name,
                parent_code,
                level,
                industry_code,
                is_pub,
                src
            FROM index.index_classify
            WHERE {where_sql}
            ORDER BY level, parent_code, index_code
            OFFSET :skip LIMIT :limit
        """)
        rows = session.execute(sql_data, params)
        items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
        return items, total

    @staticmethod
    def get_index_member_all_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        l1_code: str | None = None,
        l2_code: str | None = None,
        l3_code: str | None = None,
        ts_code: str | None = None,
        is_new: str = "Y",
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取申万行业成分构成列表
        从 index.index_member_all 表查询
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit, "is_new": is_new}
        where: list[str] = ["is_new = :is_new"]
        
        if l1_code:
            where.append("l1_code = :l1_code")
            params["l1_code"] = l1_code
        if l2_code:
            where.append("l2_code = :l2_code")
            params["l2_code"] = l2_code
        if l3_code:
            where.append("l3_code = :l3_code")
            params["l3_code"] = l3_code
        if ts_code:
            where.append("ts_code = :ts_code")
            params["ts_code"] = ts_code
            
        where_sql = " AND ".join(where)
        
        sql_count = text(f"""
            SELECT COUNT(*) AS total
            FROM index.index_member_all
            WHERE {where_sql}
        """)
        total = int(session.execute(sql_count, params).scalar() or 0)
        
        sql_data = text(f"""
            SELECT 
                l1_code, l1_name,
                l2_code, l2_name,
                l3_code, l3_name,
                ts_code, name,
                in_date::text as in_date,
                out_date::text as out_date,
                is_new
            FROM index.index_member_all
            WHERE {where_sql}
            ORDER BY l3_code, ts_code
            OFFSET :skip LIMIT :limit
        """)
        rows = session.execute(sql_data, params)
        items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
        return items, total

    @staticmethod
    def get_sw_daily_list(
        session: Session,
        ts_code: str | list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        获取申万行业日线行情列表
        从 index.sw_daily 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        where: list[str] = ["TRUE"]
        params: dict[str, Any] = {"limit": limit}

        if ts_code:
            # 支持字符串（单个或逗号分隔）、列表
            if isinstance(ts_code, str):
                codes = [c.strip() for c in ts_code.split(',') if c.strip()]
            else:
                codes = ts_code
            
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
        if start_date:
            where.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where)
        
        sql = text(f"""
            SELECT 
                ts_code,
                trade_date::text as trade_date,
                name,
                open, low, high, close,
                change, pct_change, vol, amount,
                pe, pb, float_mv, total_mv
            FROM index.sw_daily
            WHERE {where_sql}
            ORDER BY trade_date DESC
            LIMIT :limit
        """)
        
        rows = session.execute(sql, params)
        items: list[dict[str, Any]] = []
        for row in rows:
            r = dict(row._mapping)
            for k, v in r.items():
                if k not in ['ts_code', 'trade_date', 'name'] and v is not None:
                    try:
                        r[k] = float(v)
                    except (ValueError, TypeError):
                        pass
            items.append(r)
            
        return items

    @staticmethod
    def get_index_global_list(
        session: Session,
        ts_code: str | list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        获取国际指数列表
        从 index.index_global 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        where: list[str] = ["TRUE"]
        params: dict[str, Any] = {"limit": limit}

        if ts_code:
            # 支持字符串（单个或逗号分隔）、列表
            if isinstance(ts_code, str):
                codes = [c.strip() for c in ts_code.split(',') if c.strip()]
            else:
                codes = ts_code
            
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
        if start_date:
            where.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where)
        
        sql = text(f"""
            SELECT 
                ts_code,
                trade_date::text as trade_date,
                open, close, high, low, pre_close,
                change, pct_chg, swing, vol, amount
            FROM index.index_global
            WHERE {where_sql}
            ORDER BY trade_date DESC
            LIMIT :limit
        """)
        
        rows = session.execute(sql, params)
        items: list[dict[str, Any]] = []
        for row in rows:
            r = dict(row._mapping)
            for k, v in r.items():
                if k not in ['ts_code', 'trade_date'] and v is not None:
                    try:
                        r[k] = float(v)
                    except (ValueError, TypeError):
                        pass
            items.append(r)
            
        return items

    @staticmethod
    def get_index_factor_list(
        session: Session,
        ts_code: str | list[str],
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000
    ) -> list[dict[str, Any]]:
        """
        获取指数技术因子数据 (index.index_factor)
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        where: list[str] = []
        params: dict[str, Any] = {"limit": limit}
        
        # 处理 ts_code
        if isinstance(ts_code, str):
            codes = [c.strip() for c in ts_code.split(',') if c.strip()]
        else:
            codes = ts_code
        
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
        
        if not where:
            where.append("TRUE")

        if start_date:
            where.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where.append("trade_date <= :end_date")
            params["end_date"] = end_date

        where_sql = " AND ".join(where)
        
        sql = text(f"""
            SELECT 
                ts_code,
                trade_date::text as trade_date,
                open, high, low, close, pre_close,
                change, pct_change, vol, amount,
                macd_bfq, macd_dif_bfq, macd_dea_bfq,
                rsi_bfq_6, rsi_bfq_12, rsi_bfq_24,
                kdj_bfq, kdj_k_bfq, kdj_d_bfq,
                ma_bfq_5, ma_bfq_10, ma_bfq_20, ma_bfq_30, ma_bfq_60, ma_bfq_90, ma_bfq_250,
                ema_bfq_5, ema_bfq_10, ema_bfq_20, ema_bfq_30, ema_bfq_60, ema_bfq_90, ema_bfq_250,
                boll_upper_bfq, boll_mid_bfq, boll_lower_bfq
            FROM index.index_factor
            WHERE {where_sql}
            ORDER BY trade_date DESC
            LIMIT :limit
        """)
        
        rows = session.execute(sql, params)
        items: list[dict[str, Any]] = []
        for row in rows:
            r = dict(row._mapping)
            # Ensure numeric fields are float
            for k, v in r.items():
                if k not in ['ts_code', 'trade_date'] and v is not None:
                    try:
                        r[k] = float(v)
                    except (ValueError, TypeError):
                        pass
            items.append(r)
            
        return items

