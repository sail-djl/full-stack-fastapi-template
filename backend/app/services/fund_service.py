"""基金数据查询服务 - 从 fund.fund_basic 和 fund.fund_nav 表查询数据"""
from typing import Any
from datetime import timedelta, date
from sqlalchemy import text
from sqlmodel import Session


class FundService:
    """基金数据查询服务"""

    @staticmethod
    def get_fund_list(session: Session) -> list[dict[str, Any]]:
        """
        获取基金列表（包含最新净值信息）
        从 fund.fund_basic 和 fund.fund_nav 表查询
        """
        sql = text("""
            SELECT 
                b.ts_code as code,
                b.name,
                COALESCE(n.unit_nav, 0) as price,
                COALESCE(n.pct_chg, 0) as changePercent,
                n.nav_date::text as navDate
            FROM fund.fund_basic b
            LEFT JOIN LATERAL (
                SELECT unit_nav, pct_chg, nav_date
                FROM fund.fund_nav
                WHERE ts_code = b.ts_code
                ORDER BY nav_date DESC
                LIMIT 1
            ) n ON true
            WHERE b.status = 'L'  -- 只查询上市中的基金
            ORDER BY b.ts_code
        """)
        
        result = session.execute(sql)
        funds = []
        for row in result:
            # 使用 row._mapping 获取字段，但需要处理字段名大小写问题
            row_dict = dict(row._mapping)
            # 构建新的字典，确保字段名为驼峰命名
            # 处理 changePercent 字段（可能被转换为小写）
            change_percent = row_dict.get('changePercent') or row_dict.get('changepercent') or row_dict.get('CHANGEPERCENT') or 0
            # 处理 navDate 字段（可能被转换为小写）
            nav_date = row_dict.get('navDate') or row_dict.get('navdate') or row_dict.get('NAVDATE')
            
            fund_dict = {
                'code': row_dict.get('code') or row_dict.get('CODE'),
                'name': row_dict.get('name') or row_dict.get('NAME'),
                'price': float(row_dict.get('price') or row_dict.get('PRICE') or 0),
                'changePercent': float(change_percent) if change_percent else 0,
                'navDate': FundService._process_nav_date(nav_date)
            }
            funds.append(fund_dict)
        return funds
    
    @staticmethod
    def _process_nav_date(nav_date):
        """处理 navDate 字段，确保格式正确"""
        if nav_date is None or nav_date == 'None' or str(nav_date).strip() == '':
            return None
        return str(nav_date)

    @staticmethod
    def get_deviation_data(
        session: Session,
        fund1_code: str,
        fund2_code: str,
        time_range: int
    ) -> list[dict[str, Any]]:
        """
        获取偏差数据（从 fund.fund_nav 计算）
        计算两个基金的涨跌幅差值作为偏差值：deviation = fund1.pct_chg - fund2.pct_chg
        """
        # 计算起始日期
        start_date = date.today() - timedelta(days=time_range)
        
        sql = text("""
            WITH fund1_data AS (
                SELECT nav_date, pct_chg
                FROM fund.fund_nav
                WHERE ts_code = :fund1_code
                    AND nav_date >= :start_date
                    AND pct_chg IS NOT NULL
                ORDER BY nav_date
            ),
            fund2_data AS (
                SELECT nav_date, pct_chg
                FROM fund.fund_nav
                WHERE ts_code = :fund2_code
                    AND nav_date >= :start_date
                    AND pct_chg IS NOT NULL
                ORDER BY nav_date
            )
            SELECT 
                COALESCE(f1.nav_date, f2.nav_date)::text as date,
                COALESCE(f1.pct_chg, 0) - COALESCE(f2.pct_chg, 0) as deviation,
                COALESCE(f1.pct_chg, 0) as etf1PctChg,
                COALESCE(f2.pct_chg, 0) as etf2PctChg
            FROM fund1_data f1
            FULL OUTER JOIN fund2_data f2 ON f1.nav_date = f2.nav_date
            WHERE f1.pct_chg IS NOT NULL AND f2.pct_chg IS NOT NULL
            ORDER BY COALESCE(f1.nav_date, f2.nav_date)
        """).bindparams(
            fund1_code=fund1_code,
            fund2_code=fund2_code,
            start_date=start_date
        )
        
        result = session.execute(sql)
        deviation_list = []
        for row in result:
            row_dict = dict(row._mapping)
            # 处理字段名大小写问题，确保返回驼峰命名
            deviation_dict = {
                'date': row_dict.get('date') or row_dict.get('DATE'),
                'deviation': float(row_dict.get('deviation') or row_dict.get('DEVIATION') or 0),
                'etf1PctChg': float(row_dict.get('etf1PctChg') or row_dict.get('etf1pctchg') or row_dict.get('ETF1PCTCHG') or 0),
                'etf2PctChg': float(row_dict.get('etf2PctChg') or row_dict.get('etf2pctchg') or row_dict.get('ETF2PCTCHG') or 0),
            }
            deviation_list.append(deviation_dict)
        return deviation_list

    @staticmethod
    def get_deviation_summary(
        session: Session,
        fund1_code: str,
        fund2_code: str
    ) -> dict[str, Any]:
        """
        获取偏差摘要（今日、周、月、年平均偏差）
        偏差 = fund1.pct_chg - fund2.pct_chg（涨跌幅差值）
        """
        sql = text("""
            WITH deviation_calc AS (
                SELECT 
                    f1.nav_date,
                    (f1.pct_chg - f2.pct_chg) as deviation
                FROM fund.fund_nav f1
                JOIN fund.fund_nav f2 ON f1.nav_date = f2.nav_date
                WHERE f1.ts_code = :fund1_code
                    AND f2.ts_code = :fund2_code
                    AND f1.nav_date >= CURRENT_DATE - INTERVAL '365 days'
                    AND f1.pct_chg IS NOT NULL
                    AND f2.pct_chg IS NOT NULL
                ORDER BY f1.nav_date
            ),
            latest_date AS (
                SELECT MAX(nav_date) as max_date
                FROM fund.fund_nav
                WHERE ts_code = :fund1_code
            )
            SELECT 
                MAX(CASE 
                    WHEN dc.nav_date = ld.max_date THEN dc.deviation 
                END) as today,
                AVG(CASE 
                    WHEN dc.nav_date >= CURRENT_DATE - INTERVAL '7 days' THEN dc.deviation 
                END) as weekAvg,
                AVG(CASE 
                    WHEN dc.nav_date >= CURRENT_DATE - INTERVAL '30 days' THEN dc.deviation 
                END) as monthAvg,
                AVG(dc.deviation) as yearAvg
            FROM deviation_calc dc
            CROSS JOIN latest_date ld
        """).bindparams(
            fund1_code=fund1_code,
            fund2_code=fund2_code
        )
        
        result = session.execute(sql).first()
        if result:
            row = dict(result._mapping)
            return {
                'today': float(row.get('today', 0) or 0),
                'weekAvg': float(row.get('weekAvg', 0) or 0),
                'monthAvg': float(row.get('monthAvg', 0) or 0),
                'yearAvg': float(row.get('yearAvg', 0) or 0),
            }
        return {
            'today': 0.0,
            'weekAvg': 0.0,
            'monthAvg': 0.0,
            'yearAvg': 0.0,
        }

    @staticmethod
    def get_polarization_data(
        session: Session,
        fund1_code: str,
        fund2_code: str
    ) -> dict[str, Any]:
        """
        获取偏振度数据（从 fund.fund_nav 计算）
        偏振度 = |fund1.pct_chg - fund2.pct_chg| （大的数减去小的数的绝对值）
        计算当前偏振度和3年平均偏振度
        """
        sql = text("""
            WITH polarization_calc AS (
                SELECT 
                    f1.nav_date,
                    CASE 
                        WHEN f1.pct_chg >= f2.pct_chg THEN f1.pct_chg - f2.pct_chg
                        ELSE f2.pct_chg - f1.pct_chg
                    END as polarization
                FROM fund.fund_nav f1
                JOIN fund.fund_nav f2 ON f1.nav_date = f2.nav_date
                WHERE f1.ts_code = :fund1_code
                    AND f2.ts_code = :fund2_code
                    AND f1.nav_date >= CURRENT_DATE - INTERVAL '3 years'
                    AND f1.pct_chg IS NOT NULL
                    AND f2.pct_chg IS NOT NULL
                ORDER BY f1.nav_date DESC
            ),
            current_polar AS (
                SELECT polarization 
                FROM polarization_calc 
                ORDER BY nav_date DESC 
                LIMIT 1
            ),
            avg_polar AS (
                SELECT AVG(polarization) as avg_polarization
                FROM polarization_calc
            ),
            prev_polar AS (
                SELECT polarization 
                FROM polarization_calc 
                ORDER BY nav_date DESC 
                OFFSET 5 LIMIT 1
            )
            SELECT 
                cp.polarization as currentPolarization,
                COALESCE(ap.avg_polarization, 0) as avgPolarization,
                CASE 
                    WHEN cp.polarization < ap.avg_polarization * 0.85 THEN 'low'
                    WHEN cp.polarization > ap.avg_polarization * 1.15 THEN 'high'
                    ELSE 'moderate'
                END as status,
                CASE 
                    WHEN pp.polarization IS NOT NULL THEN
                        CASE 
                            WHEN cp.polarization > pp.polarization THEN 'rising'
                            WHEN cp.polarization < pp.polarization THEN 'falling'
                            ELSE 'stable'
                        END
                    ELSE 'stable'
                END as trend
            FROM current_polar cp
            CROSS JOIN avg_polar ap
            LEFT JOIN prev_polar pp ON true
        """).bindparams(
            fund1_code=fund1_code,
            fund2_code=fund2_code
        )
        
        result = session.execute(sql).first()
        if result:
            row = dict(result._mapping)
            return {
                'currentPolarization': float(row.get('currentPolarization', 0) or 0),
                'avgPolarization': float(row.get('avgPolarization', 0) or 0),
                'status': row.get('status', 'moderate'),
                'trend': row.get('trend', 'stable'),
            }
        return {
            'currentPolarization': 0.0,
            'avgPolarization': 0.0,
            'status': 'moderate',
            'trend': 'stable',
        }

    @staticmethod
    def get_accumulative_data(
        session: Session,
        fund1_code: str,
        fund2_code: str,
        time_range: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> list[dict[str, Any]]:
        """
        获取累加数据（从 fund.fund_nav 计算）
        稳定线：每日 (pct_chg1 + pct_chg2) / 2 的累加
        收益线：每日 (稳定线 * 0.8 + MAX(pct_chg1, pct_chg2) * 0.1) 的累加
        
        支持两种查询方式：
        1. 使用 time_range（天数）
        2. 使用 start_date 和 end_date（日期范围，格式：YYYY-MM-DD）
        """
        # 确定查询的日期范围
        if start_date and end_date:
            # 使用自定义日期范围
            query_start_date = date.fromisoformat(start_date)
            query_end_date = date.fromisoformat(end_date)
        elif time_range:
            # 使用固定时间范围
            query_end_date = date.today()
            query_start_date = query_end_date - timedelta(days=time_range)
        else:
            # 默认使用1年
            query_end_date = date.today()
            query_start_date = query_end_date - timedelta(days=365)
        
        sql = text("""
            SELECT 
                f1.nav_date::text as date,
                f1.pct_chg as pct_chg1,
                f2.pct_chg as pct_chg2,
                (f1.pct_chg + f2.pct_chg) / 2.0 as stable_value,
                ((f1.pct_chg + f2.pct_chg) / 2.0 * 0.8) + (GREATEST(f1.pct_chg, f2.pct_chg) * 0.1) as profit_value
            FROM fund.fund_nav f1
            JOIN fund.fund_nav f2 ON f1.nav_date = f2.nav_date
            WHERE f1.ts_code = :fund1_code
                AND f2.ts_code = :fund2_code
                AND f1.nav_date >= :start_date
                AND f1.nav_date <= :end_date
                AND f1.pct_chg IS NOT NULL
                AND f2.pct_chg IS NOT NULL
            ORDER BY f1.nav_date
        """).bindparams(
            fund1_code=fund1_code,
            fund2_code=fund2_code,
            start_date=query_start_date,
            end_date=query_end_date
        )
        
        result = session.execute(sql)
        data_list = []
        stable_accumulative = 0.0
        profit_accumulative = 0.0
        
        for row in result:
            row_dict = dict(row._mapping)
            stable_value = float(row_dict.get('stable_value', 0) or 0)
            profit_value = float(row_dict.get('profit_value', 0) or 0)
            
            # 累加计算
            stable_accumulative += stable_value
            profit_accumulative += profit_value
            
            data_list.append({
                'date': row_dict.get('date'),
                'stableLine': round(stable_accumulative, 4),
                'profitLine': round(profit_accumulative, 4),
            })
        
        return data_list

    @staticmethod
    def get_fund_basic_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        keyword: str | None = None,
        market: str | None = None,
        status: str | None = None,
        fund_type: str | None = None,
        management: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        where: list[str] = ["TRUE"]
        if keyword:
            params["kw"] = f"%{keyword}%"
            where.append("(ts_code ILIKE :kw OR name ILIKE :kw OR management ILIKE :kw OR fund_type ILIKE :kw)")
        if market:
            params["market"] = market
            where.append("market = :market")
        if status:
            params["status"] = status
            where.append("status = :status")
        if fund_type:
            params["fund_type"] = fund_type
            where.append("fund_type = :fund_type")
        if management:
            params["management"] = management
            where.append("management = :management")
        where_sql = " AND ".join(where)
        sql_count = text(f"""
            SELECT COUNT(*) AS total
            FROM fund.fund_basic
            WHERE {where_sql}
        """)
        total = int(session.execute(sql_count, params).scalar() or 0)
        sql_data = text(f"""
            SELECT 
                ts_code,
                name,
                management,
                custodian,
                fund_type,
                invest_type,
                type,
                found_date::text as found_date,
                list_date::text as list_date,
                status,
                market,
                m_fee,
                c_fee,
                update_time::text as update_time,
                create_time::text as create_time
            FROM fund.fund_basic
            WHERE {where_sql}
            ORDER BY ts_code
            OFFSET :skip LIMIT :limit
        """)
        rows = session.execute(sql_data, params)
        items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
        return items, total

    @staticmethod
    def get_fund_factor_list(
        session: Session,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000
    ) -> list[dict[str, Any]]:
        """
        获取基金技术面因子数据 (fund.fund_factor_pro)
        """
        where: list[str] = ["ts_code = :ts_code"]
        params: dict[str, Any] = {"ts_code": ts_code, "limit": limit}

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
                turnover_rate, turnover_rate_f,
                pe, pe_ttm, pb, ps, ps_ttm,
                dv_ratio, dv_ttm, total_share, float_share,
                free_share, total_mv, circ_mv
            FROM fund.fund_factor_pro
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
