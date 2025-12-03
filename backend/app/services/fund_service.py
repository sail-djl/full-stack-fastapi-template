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
        计算两个基金的净值比值作为偏差值
        """
        # 计算起始日期
        start_date = date.today() - timedelta(days=time_range)
        
        sql = text("""
            WITH fund1_data AS (
                SELECT nav_date, unit_nav as price
                FROM fund.fund_nav
                WHERE ts_code = :fund1_code
                    AND nav_date >= :start_date
                    AND unit_nav IS NOT NULL
                ORDER BY nav_date
            ),
            fund2_data AS (
                SELECT nav_date, unit_nav as price
                FROM fund.fund_nav
                WHERE ts_code = :fund2_code
                    AND nav_date >= :start_date
                    AND unit_nav IS NOT NULL
                ORDER BY nav_date
            )
            SELECT 
                COALESCE(f1.nav_date, f2.nav_date)::text as date,
                CASE 
                    WHEN f2.price > 0 THEN (f1.price / f2.price)
                    ELSE NULL
                END as deviation,
                COALESCE(f1.price, 0) as etf1Price,
                COALESCE(f2.price, 0) as etf2Price
            FROM fund1_data f1
            FULL OUTER JOIN fund2_data f2 ON f1.nav_date = f2.nav_date
            WHERE f1.price IS NOT NULL AND f2.price IS NOT NULL
            ORDER BY COALESCE(f1.nav_date, f2.nav_date)
        """).bindparams(
            fund1_code=fund1_code,
            fund2_code=fund2_code,
            start_date=start_date
        )
        
        result = session.execute(sql)
        return [dict(row._mapping) for row in result]

    @staticmethod
    def get_deviation_summary(
        session: Session,
        fund1_code: str,
        fund2_code: str
    ) -> dict[str, Any]:
        """
        获取偏差摘要（今日、周、月、年平均偏差）
        """
        sql = text("""
            WITH deviation_calc AS (
                SELECT 
                    f1.nav_date,
                    (f1.unit_nav / NULLIF(f2.unit_nav, 0)) as deviation
                FROM fund.fund_nav f1
                JOIN fund.fund_nav f2 ON f1.nav_date = f2.nav_date
                WHERE f1.ts_code = :fund1_code
                    AND f2.ts_code = :fund2_code
                    AND f1.nav_date >= CURRENT_DATE - INTERVAL '365 days'
                    AND f1.unit_nav IS NOT NULL
                    AND f2.unit_nav IS NOT NULL
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
        计算当前偏振度和3年平均偏振度
        """
        sql = text("""
            WITH polarization_calc AS (
                SELECT 
                    f1.nav_date,
                    (f1.unit_nav / NULLIF(f2.unit_nav, 0)) as polarization
                FROM fund.fund_nav f1
                JOIN fund.fund_nav f2 ON f1.nav_date = f2.nav_date
                WHERE f1.ts_code = :fund1_code
                    AND f2.ts_code = :fund2_code
                    AND f1.nav_date >= CURRENT_DATE - INTERVAL '3 years'
                    AND f1.unit_nav IS NOT NULL
                    AND f2.unit_nav IS NOT NULL
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

