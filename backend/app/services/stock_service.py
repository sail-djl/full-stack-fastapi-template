"""股票数据查询服务 - 从 stock schema 下的各个表查询数据"""
from typing import Any
import logging
from datetime import timedelta, date
from sqlalchemy import text
from sqlmodel import Session

logger = logging.getLogger(__name__)


class StockService:
    """股票数据查询服务"""

    @staticmethod
    def get_stock_basic_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        keyword: str | None = None,
        ts_code: str | list[str] | None = None,
        name: str | None = None,
        market: str | None = None,
        exchange: str | None = None,
        list_status: str | None = None,
        is_hs: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取股票基础信息列表
        从 stock.stock_basic 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
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
            
            if keyword:
                params["kw"] = f"%{keyword}%"
                where.append("(ts_code ILIKE :kw OR symbol ILIKE :kw OR name ILIKE :kw OR fullname ILIKE :kw)")
            
            if name:
                params["name"] = f"%{name}%"
                where.append("name ILIKE :name")
            
            if market:
                params["market"] = market
                where.append("market = :market")
            
            if exchange:
                params["exchange"] = exchange
                where.append("exchange = :exchange")
            
            if list_status:
                params["list_status"] = list_status
                where.append("list_status = :list_status")
            
            if is_hs:
                params["is_hs"] = is_hs
                where.append("is_hs = :is_hs")
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.stock_basic
                WHERE {where_sql}
            """)
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT 
                    ts_code,
                    symbol,
                    name,
                    area,
                    industry,
                    fullname,
                    enname,
                    cnspell,
                    market,
                    exchange,
                    curr_type,
                    list_status,
                    list_date::text as list_date,
                    delist_date::text as delist_date,
                    is_hs,
                    act_name,
                    act_ent_type,
                    update_time::text as update_time,
                    create_time::text as create_time
                FROM stock.stock_basic
                WHERE {where_sql}
                ORDER BY ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询股票基础信息失败: {e} | 参数: keyword={keyword}, ts_code={ts_code}, name={name}, market={market}, exchange={exchange}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_company_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | list[str] | None = None,
        exchange: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取上市公司基本信息列表
        从 stock.stock_company 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
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
            
            if exchange:
                params["exchange"] = exchange
                where.append("exchange = :exchange")
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.stock_company
                WHERE {where_sql}
            """)
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT 
                    ts_code,
                    com_name,
                    com_id,
                    exchange,
                    chairman,
                    manager,
                    secretary,
                    reg_capital,
                    setup_date::text as setup_date,
                    province,
                    city,
                    office,
                    website,
                    email,
                    employees,
                    main_business,
                    business_scope,
                    introduction,
                    update_time::text as update_time,
                    create_time::text as create_time
                FROM stock.stock_company
                WHERE {where_sql}
                ORDER BY ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询上市公司基本信息失败: {e} | 参数: ts_code={ts_code}, exchange={exchange}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_ipo_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        ipo_start_date: str | None = None,
        ipo_end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取IPO新股列表
        从 stock.new_share 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
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
            
            # 上市日期范围查询
            if start_date:
                where.append("issue_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("issue_date <= :end_date")
                params["end_date"] = end_date
            
            # 发行日期范围查询
            if ipo_start_date:
                where.append("ipo_date >= :ipo_start_date")
                params["ipo_start_date"] = ipo_start_date
            if ipo_end_date:
                where.append("ipo_date <= :ipo_end_date")
                params["ipo_end_date"] = ipo_end_date
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.new_share
                WHERE {where_sql}
            """)
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT 
                    ts_code,
                    sub_code,
                    name,
                    ipo_date::text as ipo_date,
                    issue_date::text as issue_date,
                    amount,
                    market_amount,
                    price,
                    pe,
                    limit_amount,
                    funds,
                    ballot,
                    update_time::text as update_time,
                    create_time::text as create_time
                FROM stock.new_share
                WHERE {where_sql}
                ORDER BY ipo_date DESC NULLS LAST, issue_date DESC NULLS LAST
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询IPO新股列表失败: {e} | 参数: ts_code={ts_code}, start_date={start_date}, end_date={end_date}, ipo_start_date={ipo_start_date}, ipo_end_date={ipo_end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_daily_list(
        session: Session,
        ts_code: str | list[str] | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        skip: int = 0,
        limit: int = 1000,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取A股日线行情列表
        从 stock.stock_daily 表查询（分区表）
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            where: list[str] = ["TRUE"]
            params: dict[str, Any] = {"skip": skip, "limit": limit}

            if ts_code:
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
            
            # 先查询总数
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.stock_daily
                WHERE {where_sql}
            """)
            count_result = session.execute(sql_count, {k: v for k, v in params.items() if k not in ['skip', 'limit']})
            total = count_result.scalar() or 0
            
            # 查询数据
            sql = text(f"""
                SELECT 
                    ts_code,
                    trade_date::text as trade_date,
                    open, high, low, close, pre_close,
                    change, pct_chg, vol, amount
                FROM stock.stock_daily
                WHERE {where_sql}
                ORDER BY trade_date DESC
                LIMIT :limit OFFSET :skip
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
                
            return items, total
        except Exception as e:
            logger.error(f"查询A股日线行情列表失败: {e} | 参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_dailybasic_list(
        session: Session,
        ts_code: str | list[str] | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        skip: int = 0,
        limit: int = 1000,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取股票每日指标列表
        从 stock.stock_dailybasic 表查询（分区表）
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            where: list[str] = ["TRUE"]
            params: dict[str, Any] = {"skip": skip, "limit": limit}

            if ts_code:
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
            
            # 先查询总数
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.stock_dailybasic
                WHERE {where_sql}
            """)
            count_result = session.execute(sql_count, {k: v for k, v in params.items() if k not in ['skip', 'limit']})
            total = count_result.scalar() or 0
            
            # 查询数据
            sql = text(f"""
                SELECT 
                    ts_code,
                    trade_date::text as trade_date,
                    close,
                    turnover_rate,
                    turnover_rate_f,
                    volume_ratio,
                    pe,
                    pe_ttm,
                    pb,
                    ps,
                    ps_ttm,
                    dv_ratio,
                    dv_ttm,
                    total_share,
                    float_share,
                    free_share,
                    total_mv,
                    circ_mv
                FROM stock.stock_dailybasic
                WHERE {where_sql}
                ORDER BY trade_date DESC
                LIMIT :limit OFFSET :skip
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
                
            return items, total
        except Exception as e:
            logger.error(f"查询股票每日指标列表失败: {e} | 参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_income_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | list[str] | None = None,
        period: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        report_type: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取利润表列表
        从 stock.stock_income 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
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
            
            if period:
                where.append("end_date = :period")
                params["period"] = period
            if start_date:
                where.append("end_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("end_date <= :end_date")
                params["end_date"] = end_date
            if report_type:
                where.append("report_type = :report_type")
                params["report_type"] = report_type
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.stock_income
                WHERE {where_sql}
            """)
            total = int(session.execute(sql_count, {k: v for k, v in params.items() if k not in ['skip', 'limit']}).scalar() or 0)
            
            sql_data = text(f"""
                SELECT 
                    ts_code,
                    ann_date::text as ann_date,
                    f_ann_date::text as f_ann_date,
                    end_date::text as end_date,
                    report_type,
                    comp_type,
                    end_type,
                    basic_eps,
                    diluted_eps,
                    total_revenue,
                    revenue,
                    int_income,
                    prem_earned,
                    comm_income,
                    n_commis_income,
                    n_oth_income,
                    n_oth_b_income,
                    prem_income,
                    out_prem,
                    une_prem_reser,
                    reins_income,
                    n_sec_tb_income,
                    n_sec_uw_income,
                    n_asset_mg_income,
                    oth_b_income,
                    fv_value_chg_gain,
                    invest_income,
                    ass_invest_income,
                    forex_gain,
                    total_cogs,
                    oper_cost,
                    int_exp,
                    comm_exp,
                    biz_tax_surchg,
                    sell_exp,
                    admin_exp,
                    fin_exp,
                    assets_impair_loss,
                    prem_refund,
                    compens_payout,
                    reser_insur_liab,
                    div_payt,
                    reins_exp,
                    oper_exp,
                    compens_payout_refu,
                    insur_reser_refu,
                    reins_cost_refund,
                    other_bus_cost,
                    operate_profit,
                    non_oper_income,
                    non_oper_exp,
                    nca_disploss,
                    total_profit,
                    income_tax,
                    n_income,
                    n_income_attr_p,
                    minority_gain,
                    oth_compr_income,
                    t_compr_income,
                    compr_inc_attr_p,
                    compr_inc_attr_m_s,
                    ebit,
                    ebitda,
                    insurance_exp,
                    undist_profit,
                    distable_profit,
                    rd_exp,
                    fin_exp_int_exp,
                    fin_exp_int_inc,
                    transfer_surplus_rese,
                    transfer_housing_imprest,
                    transfer_oth,
                    adj_lossgain,
                    withdra_legal_surplus,
                    withdra_legal_pubfund,
                    withdra_biz_devfund,
                    withdra_rese_fund,
                    withdra_oth_ersu,
                    workers_welfare,
                    distr_profit_shrhder,
                    prfshare_payable_dvd,
                    comshare_payable_dvd,
                    capit_comstock_div,
                    net_after_nr_lp_correct,
                    credit_impa_loss,
                    net_expo_hedging_benefits,
                    oth_impair_loss_assets,
                    total_opcost,
                    amodcost_fin_assets,
                    oth_income,
                    asset_disp_income,
                    continued_net_profit,
                    end_net_profit,
                    update_flag,
                    update_time::text as update_time,
                    create_time::text as create_time
                FROM stock.stock_income
                WHERE {where_sql}
                ORDER BY end_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询利润表列表失败: {e} | 参数: ts_code={ts_code}, period={period}, start_date={start_date}, end_date={end_date}, report_type={report_type}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_balancesheet_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | list[str] | None = None,
        period: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        report_type: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取资产负债表列表
        从 stock.stock_balancesheet 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
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
            
            if period:
                where.append("end_date = :period")
                params["period"] = period
            if start_date:
                where.append("end_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("end_date <= :end_date")
                params["end_date"] = end_date
            if report_type:
                where.append("report_type = :report_type")
                params["report_type"] = report_type
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.stock_balancesheet
                WHERE {where_sql}
            """)
            total = int(session.execute(sql_count, {k: v for k, v in params.items() if k not in ['skip', 'limit']}).scalar() or 0)
            
            # 查询所有字段，使用 SELECT * 因为字段太多
            sql_data = text(f"""
                SELECT *
                FROM stock.stock_balancesheet
                WHERE {where_sql}
                ORDER BY end_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = []
            for row in rows:
                r = dict(row._mapping)
                # 转换日期字段为字符串
                for key in ['ann_date', 'f_ann_date', 'end_date']:
                    if key in r and r[key] is not None:
                        if hasattr(r[key], 'strftime'):
                            r[key] = r[key].strftime('%Y%m%d')
                        elif isinstance(r[key], str) and len(r[key]) == 10:
                            r[key] = r[key].replace('-', '')
                # 转换时间戳字段为字符串
                for key in ['update_time', 'create_time']:
                    if key in r and r[key] is not None:
                        if hasattr(r[key], 'strftime'):
                            r[key] = r[key].strftime('%Y-%m-%d %H:%M:%S')
                items.append(r)
            return items, total
        except Exception as e:
            logger.error(f"查询资产负债表列表失败: {e} | 参数: ts_code={ts_code}, period={period}, start_date={start_date}, end_date={end_date}, report_type={report_type}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_business_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | list[str] | None = None,
        period: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取主营业务构成列表
        从 stock.fina_mainbz 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
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
            
            if period:
                where.append("end_date = :period")
                params["period"] = period
            if start_date:
                where.append("end_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("end_date <= :end_date")
                params["end_date"] = end_date
            # type 字段已从表中移除，不再作为查询条件
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.fina_mainbz
                WHERE {where_sql}
            """)
            total = int(session.execute(sql_count, {k: v for k, v in params.items() if k not in ['skip', 'limit']}).scalar() or 0)
            
            sql_data = text(f"""
                SELECT 
                    ts_code,
                    end_date::text as end_date,
                    bz_item,
                    bz_sales,
                    bz_profit,
                    bz_cost,
                    curr_type,
                    update_flag,
                    update_time::text as update_time,
                    create_time::text as create_time
                FROM stock.fina_mainbz
                WHERE {where_sql}
                ORDER BY end_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            # 处理日期格式
            for item in items:
                if 'end_date' in item and item['end_date']:
                    if isinstance(item['end_date'], str) and len(item['end_date']) == 10:
                        item['end_date'] = item['end_date'].replace('-', '')
            return items, total
        except Exception as e:
            logger.error(f"查询主营业务构成列表失败: {e} | 参数: ts_code={ts_code}, period={period}, start_date={start_date}, end_date={end_date}, type={type}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_report_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | list[str] | None = None,
        end_date: str | None = None,
        pre_date: str | None = None,
        ann_date: str | None = None,
        actual_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取财报披露日期列表
        从 stock.disclosure_date 表查询
        支持单个 ts_code 或多个 ts_code（列表或逗号分隔字符串）
        """
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
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
            
            if end_date:
                where.append("end_date = :end_date")
                params["end_date"] = end_date
            if pre_date:
                where.append("pre_date = :pre_date")
                params["pre_date"] = pre_date
            if ann_date:
                where.append("ann_date = :ann_date")
                params["ann_date"] = ann_date
            if actual_date:
                where.append("actual_date = :actual_date")
                params["actual_date"] = actual_date
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"""
                SELECT COUNT(*) AS total
                FROM stock.disclosure_date
                WHERE {where_sql}
            """)
            total = int(session.execute(sql_count, {k: v for k, v in params.items() if k not in ['skip', 'limit']}).scalar() or 0)
            
            sql_data = text(f"""
                SELECT 
                    ts_code,
                    end_date::text as end_date,
                    ann_date::text as ann_date,
                    pre_date::text as pre_date,
                    actual_date::text as actual_date,
                    modify_date::text as modify_date
                FROM stock.disclosure_date
                WHERE {where_sql}
                ORDER BY end_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = []
            for row in rows:
                r = dict(row._mapping)
                # 处理日期格式，转换为 YYYYMMDD 格式
                for key in ['end_date', 'ann_date', 'pre_date', 'actual_date', 'modify_date']:
                    if key in r and r[key] is not None:
                        if isinstance(r[key], str) and len(r[key]) == 10:
                            r[key] = r[key].replace('-', '')
                items.append(r)
            return items, total
        except Exception as e:
            logger.error(f"查询财报披露日期列表失败: {e} | 参数: ts_code={ts_code}, end_date={end_date}, pre_date={pre_date}, ann_date={ann_date}, actual_date={actual_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_shareholder_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取股东增减持列表"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
                where.append("ts_code = :ts_code")
                params["ts_code"] = ts_code
            if start_date:
                where.append("ann_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("ann_date <= :end_date")
                params["end_date"] = end_date
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.stk_holdertrade WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT ts_code, ann_date::text as ann_date, holder_name, holder_type, in_de,
                       change_vol, change_ratio, after_share, after_ratio, avg_price, total_share,
                       begin_date::text as begin_date, close_date::text as close_date
                FROM stock.stk_holdertrade
                WHERE {where_sql}
                ORDER BY ann_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询股东增减持列表失败: {e} | 参数: ts_code={ts_code}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_repurchase_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取股票回购列表"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
                where.append("ts_code = :ts_code")
                params["ts_code"] = ts_code
            if start_date:
                where.append("ann_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("ann_date <= :end_date")
                params["end_date"] = end_date
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.repurchase WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT ts_code, ann_date::text as ann_date, end_date::text as end_date, proc,
                       exp_date::text as exp_date, vol, amount, high_limit, low_limit
                FROM stock.repurchase
                WHERE {where_sql}
                ORDER BY ann_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询股票回购列表失败: {e} | 参数: ts_code={ts_code}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_margin_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        exchange_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取融资融券交易汇总列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if trade_date:
                where.append("trade_date = :trade_date")
                params["trade_date"] = trade_date
            if start_date:
                where.append("trade_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("trade_date <= :end_date")
                params["end_date"] = end_date
            if exchange_id:
                where.append("exchange_id = :exchange_id")
                params["exchange_id"] = exchange_id
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.margin WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT trade_date::text as trade_date, exchange_id, rzye, rzmre, rzche,
                       rqye, rqmcl, rzrqye, rqyl
                FROM stock.margin
                WHERE {where_sql}
                ORDER BY trade_date DESC
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询融资融券交易汇总列表失败: {e} | 参数: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, exchange_id={exchange_id}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_top_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取龙虎榜每日明细列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
                where.append("ts_code = :ts_code")
                params["ts_code"] = ts_code
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
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.top_list WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT trade_date::text as trade_date, ts_code, name, close, pct_change,
                       turnover_rate, amount, l_sell, l_buy, l_amount, net_amount,
                       net_rate, amount_rate, float_values, reason
                FROM stock.top_list
                WHERE {where_sql}
                ORDER BY trade_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询龙虎榜每日明细列表失败: {e} | 参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_recommend_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        month: str | None = None,
        broker: str | None = None,
        ts_code: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取券商每月荐股列表"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if month:
                where.append("month = :month")
                params["month"] = month
            if broker:
                where.append("broker = :broker")
                params["broker"] = broker
            if ts_code:
                where.append("ts_code = :ts_code")
                params["ts_code"] = ts_code
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.broker_recommend WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT month, broker, ts_code, name
                FROM stock.broker_recommend
                WHERE {where_sql}
                ORDER BY month DESC, broker, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询券商每月荐股列表失败: {e} | 参数: month={month}, broker={broker}, ts_code={ts_code}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_hsgt_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        exchange: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取沪深港股通持股明细列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
                where.append("ts_code = :ts_code")
                params["ts_code"] = ts_code
            if trade_date:
                where.append("trade_date = :trade_date")
                params["trade_date"] = trade_date
            if start_date:
                where.append("trade_date >= :start_date")
                params["start_date"] = start_date
            if end_date:
                where.append("trade_date <= :end_date")
                params["end_date"] = end_date
            if exchange:
                where.append("exchange = :exchange")
                params["exchange"] = exchange
                
            where_sql = " AND ".join(where)
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.hk_hold WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT code, trade_date::text as trade_date, ts_code, name, vol, ratio, exchange
                FROM stock.hk_hold
                WHERE {where_sql}
                ORDER BY trade_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询沪深港股通持股明细列表失败: {e} | 参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}, exchange={exchange}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_transfer_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取转融资交易汇总列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
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
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.slb_len WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT trade_date::text as trade_date, ob, auc_amount, repo_amount,
                       repay_amount, cb
                FROM stock.slb_len
                WHERE {where_sql}
                ORDER BY trade_date DESC
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询转融资交易汇总列表失败: {e} | 参数: trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_top_inst_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取龙虎榜机构明细列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
                where.append("ts_code = :ts_code")
                params["ts_code"] = ts_code
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
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.top_inst WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT trade_date::text as trade_date, ts_code, exalter, side,
                       buy, buy_rate, sell, sell_rate, net_buy, reason
                FROM stock.top_inst
                WHERE {where_sql}
                ORDER BY trade_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询龙虎榜机构明细列表失败: {e} | 参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_strongest_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        ts_code: str | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取最强板块统计列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
            if ts_code:
                where.append("ts_code = :ts_code")
                params["ts_code"] = ts_code
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
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.limit_cpt_list WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT ts_code, name, trade_date::text as trade_date, days, up_stat,
                       cons_nums, up_nums, pct_chg, rank
                FROM stock.limit_cpt_list
                WHERE {where_sql}
                ORDER BY trade_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询最强板块统计列表失败: {e} | 参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_ths_concept_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取同花顺概念板块资金流向列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
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
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.moneyflow_cnt_ths WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT trade_date::text as trade_date, ts_code as code, name, net_amount as net_mf_amount, 
                       CASE WHEN net_amount IS NOT NULL THEN (net_amount / NULLIF(ABS(net_amount) + ABS(COALESCE(net_sell_amount, 0)), 0) * 100) ELSE NULL END as net_mf_ratio
                FROM stock.moneyflow_cnt_ths
                WHERE {where_sql}
                ORDER BY trade_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询同花顺概念板块资金流向列表失败: {e} | 参数: trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_ths_industry_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取同花顺行业资金流向列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
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
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.moneyflow_ind_ths WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT trade_date::text as trade_date, ts_code as code, industry as name, net_amount as net_mf_amount,
                       CASE WHEN net_amount IS NOT NULL THEN (net_amount / NULLIF(ABS(net_amount) + ABS(COALESCE(net_sell_amount, 0)), 0) * 100) ELSE NULL END as net_mf_ratio
                FROM stock.moneyflow_ind_ths
                WHERE {where_sql}
                ORDER BY trade_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询同花顺行业资金流向列表失败: {e} | 参数: trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

    @staticmethod
    def get_stock_dc_concept_list(
        session: Session,
        skip: int = 0,
        limit: int = 1000,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """获取东财概念及行业板块资金流向列表（分区表）"""
        try:
            params: dict[str, Any] = {"skip": skip, "limit": limit}
            where: list[str] = ["TRUE"]
            
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
            
            sql_count = text(f"SELECT COUNT(*) AS total FROM stock.moneyflow_ind_dc WHERE {where_sql}")
            total = int(session.execute(sql_count, params).scalar() or 0)
            
            sql_data = text(f"""
                SELECT trade_date::text as trade_date, ts_code as code, name, net_amount,
                       net_amount_rate
                FROM stock.moneyflow_ind_dc
                WHERE {where_sql}
                ORDER BY trade_date DESC, ts_code
                OFFSET :skip LIMIT :limit
            """)
            rows = session.execute(sql_data, params)
            items: list[dict[str, Any]] = [dict(row._mapping) for row in rows]
            return items, total
        except Exception as e:
            logger.error(f"查询东财概念及行业板块资金流向列表失败: {e} | 参数: trade_date={trade_date}, start_date={start_date}, end_date={end_date}", exc_info=True)
            raise e

