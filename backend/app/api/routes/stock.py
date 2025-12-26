import logging
import traceback
from typing import Any, Optional, List
from datetime import timedelta, date

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session
from app.api.deps import SessionDep
from app.services.stock_service import StockService
from app.core.config import settings

router = APIRouter(prefix="/stock", tags=["stock"])


# ==================== 辅助函数 ====================

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


def _get_last_date(session: Session, table: str, ts_code: str, date_col: str = "trade_date") -> Optional[date]:
    """获取指定表的最后日期"""
    sql = text(f"SELECT MAX({date_col}) AS last_date FROM {table} WHERE ts_code = :ts_code")
    with session.connection() as conn:
        row = conn.execute(sql, {"ts_code": ts_code}).fetchone()
        return row[0] if row and row[0] else None


# ==================== 列表查询接口 ====================

@router.get("/basic")
def get_stock_basic(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    keyword: str | None = None,
    ts_code: str | None = None,
    name: str | None = None,
    market: str | None = None,
    exchange: str | None = None,
    list_status: str | None = None,
    is_hs: str | None = None,
) -> Any:
    """
    获取股票基础信息列表
    支持单个 ts_code 或多个 ts_code（逗号分隔，如：000001.SZ,600000.SH）
    """
    items, total = StockService.get_stock_basic_list(
        session=session,
        skip=skip,
        limit=limit,
        keyword=keyword,
        ts_code=ts_code,
        name=name,
        market=market,
        exchange=exchange,
        list_status=list_status,
        is_hs=is_hs,
    )
    return {"data": items, "count": total}


@router.get("/company")
def get_stock_company(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    exchange: str | None = None,
) -> Any:
    """
    获取上市公司基本信息列表
    支持单个 ts_code 或多个 ts_code（逗号分隔，如：000001.SZ,600000.SH）
    """
    items, total = StockService.get_stock_company_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        exchange=exchange,
    )
    return {"data": items, "count": total}


@router.get("/ipo")
def get_stock_ipo(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    ipo_start_date: str | None = None,
    ipo_end_date: str | None = None,
) -> Any:
    """
    获取IPO新股列表
    支持单个 ts_code 或多个 ts_code（逗号分隔）
    start_date/end_date: 上市日期范围
    ipo_start_date/ipo_end_date: 发行日期范围
    """
    items, total = StockService.get_stock_ipo_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        ipo_start_date=ipo_start_date,
        ipo_end_date=ipo_end_date,
    )
    return {"data": items, "count": total}


@router.get("/daily")
def get_stock_daily(
    session: SessionDep,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """
    获取A股日线行情列表
    支持单个 ts_code 或多个 ts_code（逗号分隔）
    """
    items = StockService.get_stock_daily_list(
        session=session,
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


@router.get("/dailybasic")
def get_stock_dailybasic(
    session: SessionDep,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    skip: int = 0,
    limit: int = 1000,
) -> Any:
    """
    获取股票每日指标列表
    支持单个 ts_code 或多个 ts_code（逗号分隔）
    """
    items, total = StockService.get_stock_dailybasic_list(
        session=session,
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return {"data": items, "count": total}


class StockDailySyncPayload(BaseModel):
    ts_code: str | None = None
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/daily/sync")
def sync_stock_daily(session: SessionDep, payload: StockDailySyncPayload) -> Any:
    """同步A股日线行情"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync stock_daily request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    # 确定时间范围
    start_d = None
    if payload.start_date:
        start_d = _parse_iso_date(payload.start_date)
    elif payload.ts_code:
        last_date = _get_last_date(session, "stock.stock_daily", payload.ts_code, date_col="trade_date")
        if last_date:
            start_d = last_date + timedelta(days=1)
        else:
            start_d = date.today() - timedelta(days=365 * 2)  # 默认同步2年数据
    else:
        start_d = date.today() - timedelta(days=30)  # 如果没有指定股票代码，默认同步最近30天

    end_d = date.today()
    if payload.end_date:
        end_d = _parse_iso_date(payload.end_date)
    if payload.trade_date:
        end_d = _parse_iso_date(payload.trade_date)
        start_d = end_d

    if start_d and end_d and start_d > end_d:
        logger.info(f"No new data to sync for daily. Start date: {start_d}, End date: {end_d}")
        return {"message": "No new data to sync", "success": 0, "failed": 0}

    total_success = 0
    total_failed = 0

    # 按年循环获取
    curr = start_d if start_d else date.today() - timedelta(days=365 * 2)
    while curr <= end_d:
        next_year = curr + timedelta(days=365)
        batch_end = min(next_year, end_d)

        params = {
            "ts_code": payload.ts_code,
            "start_date": _to_yyyymmdd(curr),
            "end_date": _to_yyyymmdd(batch_end),
            "trade_date": payload.trade_date,
        }
        try:
            logger.info(f"Fetching daily with params: {params}")
            df = pro.daily(**params)

            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "stock.stock_daily", rows, ["ts_code", "trade_date"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed for daily: {e}\n{traceback.format_exc()}")
            total_failed += 1

        curr = batch_end + timedelta(days=1)

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


class StockDailybasicSyncPayload(BaseModel):
    ts_code: str | None = None
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/dailybasic/sync")
def sync_stock_dailybasic(session: SessionDep, payload: StockDailybasicSyncPayload) -> Any:
    """同步股票每日指标"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync stock_dailybasic request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    # 确定时间范围
    start_d = None
    if payload.start_date:
        start_d = _parse_iso_date(payload.start_date)
    elif payload.ts_code:
        last_date = _get_last_date(session, "stock.stock_dailybasic", payload.ts_code, date_col="trade_date")
        if last_date:
            start_d = last_date + timedelta(days=1)
        else:
            start_d = date.today() - timedelta(days=365 * 2)  # 默认同步2年数据
    else:
        start_d = date.today() - timedelta(days=30)  # 如果没有指定股票代码，默认同步最近30天

    end_d = date.today()
    if payload.end_date:
        end_d = _parse_iso_date(payload.end_date)
    if payload.trade_date:
        end_d = _parse_iso_date(payload.trade_date)
        start_d = end_d

    if start_d and end_d and start_d > end_d:
        logger.info(f"No new data to sync for dailybasic. Start date: {start_d}, End date: {end_d}")
        return {"message": "No new data to sync", "success": 0, "failed": 0}

    total_success = 0
    total_failed = 0

    # 按年循环获取
    curr = start_d if start_d else date.today() - timedelta(days=365 * 2)
    while curr <= end_d:
        next_year = curr + timedelta(days=365)
        batch_end = min(next_year, end_d)

        params = {
            "ts_code": payload.ts_code,
            "start_date": _to_yyyymmdd(curr),
            "end_date": _to_yyyymmdd(batch_end),
            "trade_date": payload.trade_date,
        }
        try:
            logger.info(f"Fetching dailybasic with params: {params}")
            df = pro.daily_basic(**params)

            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "stock.stock_dailybasic", rows, ["ts_code", "trade_date"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed for dailybasic: {e}\n{traceback.format_exc()}")
            total_failed += 1

        curr = batch_end + timedelta(days=1)

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


@router.get("/income")
def get_stock_income(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    report_type: str | None = None,
) -> Any:
    """
    获取利润表列表
    支持单个 ts_code 或多个 ts_code（逗号分隔）
    """
    items, total = StockService.get_stock_income_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        period=period,
        start_date=start_date,
        end_date=end_date,
        report_type=report_type,
    )
    return {"data": items, "count": total}


@router.get("/balancesheet")
def get_stock_balancesheet(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    report_type: str | None = None,
) -> Any:
    """
    获取资产负债表列表
    支持单个 ts_code 或多个 ts_code（逗号分隔）
    """
    items, total = StockService.get_stock_balancesheet_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        period=period,
        start_date=start_date,
        end_date=end_date,
        report_type=report_type,
    )
    return {"data": items, "count": total}


@router.get("/business")
def get_stock_business(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    period: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    type: str | None = None,
) -> Any:
    """
    获取主营业务构成列表
    支持单个 ts_code 或多个 ts_code（逗号分隔）
    """
    items, total = StockService.get_stock_business_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        period=period,
        start_date=start_date,
        end_date=end_date,
        type=type,
    )
    return {"data": items, "count": total}


@router.get("/report")
def get_stock_report(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    end_date: str | None = None,
    pre_date: str | None = None,
    ann_date: str | None = None,
    actual_date: str | None = None,
) -> Any:
    """
    获取财报披露日期列表
    支持单个 ts_code 或多个 ts_code（逗号分隔）
    """
    items, total = StockService.get_stock_report_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        end_date=end_date,
        pre_date=pre_date,
        ann_date=ann_date,
        actual_date=actual_date,
    )
    return {"data": items, "count": total}


# ==================== 同步接口 ====================

class StockBasicSyncPayload(BaseModel):
    keyword: str | None = None
    market: str | None = None
    exchange: str | None = None
    list_status: str | None = None
    is_hs: str | None = None


def _upsert_records(session: Session, table: str, records: List[dict], primary_keys: List[str]) -> tuple[int, int]:
    """通用 upsert 函数"""
    if not records:
        return 0, 0
    
    first_keys = list(records[0].keys())
    keys = [k for k in first_keys if k not in ['id', 'update_time', 'create_time']]
    
    if not all(pk in keys for pk in primary_keys):
        logger.error(f"Upsert failed: Missing primary keys {primary_keys}")
        return 0, len(records)

    # 处理日期格式 (YYYYMMDD -> YYYY-MM-DD)
    processed_records = []
    for r in records:
        new_r = {k: r.get(k) for k in keys}
        # 处理 trade_date 或类似日期字段
        for date_key in ['trade_date', 'nav_date', 'in_date', 'out_date', 'base_date', 'list_date', 'exp_date', 'delist_date', 'setup_date']:
            if date_key in new_r:
                td = new_r.get(date_key)
                if isinstance(td, str) and len(td) == 8:
                    try:
                        new_r[date_key] = f"{td[:4]}-{td[4:6]}-{td[6:]}"
                    except:
                        pass
        processed_records.append(new_r)
    
    records = processed_records

    # 构建 INSERT SQL
    cols = ", ".join(keys)
    vals = ", ".join([f":{k}" for k in keys])
    
    # 构建 UPDATE SET (排除主键)
    update_set = ", ".join([f"{k} = EXCLUDED.{k}" for k in keys if k not in primary_keys])
    
    pk_constraint = ", ".join(primary_keys)
    
    sql_str = f"""
        INSERT INTO {table} ({cols})
        VALUES ({vals})
        ON CONFLICT ({pk_constraint})
        DO UPDATE SET
            {update_set},
            update_time = CURRENT_TIMESTAMP
    """
    
    success = 0
    failed = 0
    
    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            session.execute(text(sql_str), batch)
            session.commit()
            success += len(batch)
        except Exception as e:
            logger.error(f"Upsert batch failed: {e}\n{traceback.format_exc()}")
            session.rollback()
            # 降级为逐条插入
            for rec in batch:
                try:
                    session.execute(text(sql_str), rec)
                    session.commit()
                    success += 1
                except Exception as e2:
                    logger.error(f"Upsert single failed: {e2}")
                    session.rollback()
                    failed += 1
                    
    return success, failed


@router.post("/basic/sync")
def sync_stock_basic(session: SessionDep, payload: StockBasicSyncPayload) -> Any:
    """同步股票基础信息"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync stock_basic request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.market:
            params["market"] = payload.market
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.list_status:
            params["list_status"] = payload.list_status
        if payload.is_hs:
            params["is_hs"] = payload.is_hs
        
        logger.info(f"Fetching stock_basic with params: {params}")
        df = pro.stock_basic(**params)
        
        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")
        
        # 数据清洗
        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")
        
        # 如果有关键词过滤，在同步后进行过滤
        if payload.keyword:
            keyword_lower = payload.keyword.lower()
            rows = [
                r for r in rows
                if keyword_lower in str(r.get('ts_code', '')).lower()
                or keyword_lower in str(r.get('name', '')).lower()
                or keyword_lower in str(r.get('symbol', '')).lower()
            ]
        
        succ, fail = _upsert_records(session, "stock.stock_basic", rows, ["ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}
        
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockCompanySyncPayload(BaseModel):
    ts_code: str | None = None
    exchange: str | None = None


@router.post("/company/sync")
def sync_stock_company(session: SessionDep, payload: StockCompanySyncPayload) -> Any:
    """同步上市公司基本信息"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync stock_company request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.exchange:
            params["exchange"] = payload.exchange
        
        logger.info(f"Fetching stock_company with params: {params}")
        df = pro.stock_company(**params)
        
        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")
        
        # 数据清洗
        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")
        
        succ, fail = _upsert_records(session, "stock.stock_company", rows, ["ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}
        
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockIpoSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None


@router.post("/ipo/sync")
def sync_stock_ipo(session: SessionDep, payload: StockIpoSyncPayload) -> Any:
    """同步IPO新股列表"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync new_share request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        logger.info(f"Fetching new_share with params: {params}")
        df = pro.new_share(**params)
        
        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")
        
        # 数据清洗
        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")
        
        succ, fail = _upsert_records(session, "stock.new_share", rows, ["ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}
        
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockIncomeSyncPayload(BaseModel):
    ts_code: str | None = None
    period: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/income/sync")
def sync_stock_income(session: SessionDep, payload: StockIncomeSyncPayload) -> Any:
    """同步利润表"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync income request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.ts_code:
        raise HTTPException(status_code=400, detail="必须指定股票代码")

    ts_codes = [c.strip() for c in payload.ts_code.split(',') if c.strip()]
    total_success = 0
    total_failed = 0

    for ts_code in ts_codes:
        try:
            params = {"ts_code": ts_code}
            if payload.period:
                params["period"] = payload.period
            if payload.start_date:
                params["start_date"] = payload.start_date
            if payload.end_date:
                params["end_date"] = payload.end_date

            logger.info(f"Fetching income for {ts_code} with params: {params}")
            df = pro.income(**params)

            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "stock.stock_income", rows, ["ts_code", "end_date", "report_type"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed for {ts_code}: {e}\n{traceback.format_exc()}")
            total_failed += 1

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


class StockBalancesheetSyncPayload(BaseModel):
    ts_code: str | None = None
    period: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/balancesheet/sync")
def sync_stock_balancesheet(session: SessionDep, payload: StockBalancesheetSyncPayload) -> Any:
    """同步资产负债表"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync balancesheet request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.ts_code:
        raise HTTPException(status_code=400, detail="必须指定股票代码")

    ts_codes = [c.strip() for c in payload.ts_code.split(',') if c.strip()]
    total_success = 0
    total_failed = 0

    for ts_code in ts_codes:
        try:
            params = {"ts_code": ts_code}
            if payload.period:
                params["period"] = payload.period
            if payload.start_date:
                params["start_date"] = payload.start_date
            if payload.end_date:
                params["end_date"] = payload.end_date

            logger.info(f"Fetching balancesheet for {ts_code} with params: {params}")
            df = pro.balancesheet(**params)

            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "stock.stock_balancesheet", rows, ["ts_code", "end_date", "report_type"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed for {ts_code}: {e}\n{traceback.format_exc()}")
            total_failed += 1

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


class StockBusinessSyncPayload(BaseModel):
    ts_code: str | None = None
    period: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    type: str | None = None


@router.post("/business/sync")
def sync_stock_business(session: SessionDep, payload: StockBusinessSyncPayload) -> Any:
    """同步主营业务构成"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync fina_mainbz request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.ts_code:
        raise HTTPException(status_code=400, detail="必须指定股票代码")

    ts_codes = [c.strip() for c in payload.ts_code.split(',') if c.strip()]
    total_success = 0
    total_failed = 0

    for ts_code in ts_codes:
        try:
            params = {"ts_code": ts_code}
            if payload.period:
                params["period"] = payload.period
            if payload.start_date:
                params["start_date"] = payload.start_date
            if payload.end_date:
                params["end_date"] = payload.end_date
            if payload.type:
                params["type"] = payload.type

            logger.info(f"Fetching fina_mainbz for {ts_code} with params: {params}")
            df = pro.fina_mainbz(**params)

            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "stock.fina_mainbz", rows, ["ts_code", "end_date", "bz_item", "type"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed for {ts_code}: {e}\n{traceback.format_exc()}")
            total_failed += 1

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


class StockReportSyncPayload(BaseModel):
    ts_code: str | None = None
    end_date: str | None = None


@router.post("/report/sync")
def sync_stock_report(session: SessionDep, payload: StockReportSyncPayload) -> Any:
    """同步财报披露日期"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync disclosure_date request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.end_date:
            params["end_date"] = payload.end_date

        logger.info(f"Fetching disclosure_date with params: {params}")
        df = pro.disclosure_date(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.disclosure_date", rows, ["ts_code", "end_date"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


@router.get("/shareholder")
def get_stock_shareholder(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取股东增减持列表"""
    items, total = StockService.get_stock_shareholder_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


@router.get("/repurchase")
def get_stock_repurchase(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取股票回购列表"""
    items, total = StockService.get_stock_repurchase_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


@router.get("/margin")
def get_stock_margin(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    exchange_id: str | None = None,
) -> Any:
    """获取融资融券交易汇总列表"""
    items, total = StockService.get_stock_margin_list(
        session=session,
        skip=skip,
        limit=limit,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        exchange_id=exchange_id,
    )
    return {"data": items, "count": total}


@router.get("/toplist")
def get_stock_top_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取龙虎榜每日明细列表"""
    items, total = StockService.get_stock_top_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


class StockShareholderSyncPayload(BaseModel):
    ts_code: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/shareholder/sync")
def sync_stock_shareholder(session: SessionDep, payload: StockShareholderSyncPayload) -> Any:
    """同步股东增减持"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync stk_holdertrade request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date

        logger.info(f"Fetching stk_holdertrade with params: {params}")
        df = pro.stk_holdertrade(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.stk_holdertrade", rows, ["ts_code", "ann_date", "holder_name", "in_de"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockRepurchaseSyncPayload(BaseModel):
    ts_code: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/repurchase/sync")
def sync_stock_repurchase(session: SessionDep, payload: StockRepurchaseSyncPayload) -> Any:
    """同步股票回购"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync repurchase request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date

        logger.info(f"Fetching repurchase with params: {params}")
        df = pro.repurchase(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.repurchase", rows, ["ts_code", "ann_date"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockMarginSyncPayload(BaseModel):
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    exchange_id: str | None = None


@router.post("/margin/sync")
def sync_stock_margin(session: SessionDep, payload: StockMarginSyncPayload) -> Any:
    """同步融资融券交易汇总"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync margin request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.trade_date:
            params["trade_date"] = payload.trade_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        if payload.exchange_id:
            params["exchange_id"] = payload.exchange_id

        logger.info(f"Fetching margin with params: {params}")
        df = pro.margin(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.margin", rows, ["trade_date", "exchange_id"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockTopListSyncPayload(BaseModel):
    trade_date: str  # 必填参数
    ts_code: str | None = None  # 可选参数


@router.post("/toplist/sync")
def sync_stock_top_list(session: SessionDep, payload: StockTopListSyncPayload) -> Any:
    """同步龙虎榜每日明细"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync top_list request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {"trade_date": payload.trade_date}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code

        logger.info(f"Fetching top_list with params: {params}")
        df = pro.top_list(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.top_list", rows, ["trade_date", "ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


@router.get("/recommend")
def get_stock_recommend(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    month: str | None = None,
    broker: str | None = None,
    ts_code: str | None = None,
) -> Any:
    """获取券商每月荐股列表"""
    items, total = StockService.get_stock_recommend_list(
        session=session,
        skip=skip,
        limit=limit,
        month=month,
        broker=broker,
        ts_code=ts_code,
    )
    return {"data": items, "count": total}


@router.get("/hsgt")
def get_stock_hsgt(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    exchange: str | None = None,
) -> Any:
    """获取沪深港股通持股明细列表"""
    items, total = StockService.get_stock_hsgt_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        exchange=exchange,
    )
    return {"data": items, "count": total}


@router.get("/transfer")
def get_stock_transfer(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取转融资交易汇总列表"""
    items, total = StockService.get_stock_transfer_list(
        session=session,
        skip=skip,
        limit=limit,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


@router.get("/topinst")
def get_stock_top_inst(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取龙虎榜机构明细列表"""
    items, total = StockService.get_stock_top_inst_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


@router.get("/strongest")
def get_stock_strongest(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取最强板块统计列表"""
    items, total = StockService.get_stock_strongest_list(
        session=session,
        skip=skip,
        limit=limit,
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


@router.get("/thsconcept")
def get_stock_ths_concept(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取同花顺概念板块资金流向列表"""
    items, total = StockService.get_stock_ths_concept_list(
        session=session,
        skip=skip,
        limit=limit,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


@router.get("/thsindustry")
def get_stock_ths_industry(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取同花顺行业资金流向列表"""
    items, total = StockService.get_stock_ths_industry_list(
        session=session,
        skip=skip,
        limit=limit,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


@router.get("/dcconcept")
def get_stock_dc_concept(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """获取东财概念及行业板块资金流向列表"""
    items, total = StockService.get_stock_dc_concept_list(
        session=session,
        skip=skip,
        limit=limit,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return {"data": items, "count": total}


class StockRecommendSyncPayload(BaseModel):
    month: str | None = None
    broker: str | None = None
    ts_code: str | None = None


@router.post("/recommend/sync")
def sync_stock_recommend(session: SessionDep, payload: StockRecommendSyncPayload) -> Any:
    """同步券商每月荐股"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync broker_recommend request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        if not payload.month:
            raise HTTPException(status_code=400, detail="月份（month）为必填参数")

        params = {}
        params["month"] = payload.month
        if payload.broker:
            params["broker"] = payload.broker
        if payload.ts_code:
            params["ts_code"] = payload.ts_code

        logger.info(f"Fetching broker_recommend with params: {params}")
        df = pro.broker_recommend(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.broker_recommend", rows, ["month", "broker", "ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockHsgtSyncPayload(BaseModel):
    ts_code: str | None = None
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    exchange: str | None = None


@router.post("/hsgt/sync")
def sync_stock_hsgt(session: SessionDep, payload: StockHsgtSyncPayload) -> Any:
    """同步沪深港股通持股明细"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync hk_hold request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.trade_date:
            params["trade_date"] = payload.trade_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        if payload.exchange:
            params["exchange"] = payload.exchange

        logger.info(f"Fetching hk_hold with params: {params}")
        df = pro.hk_hold(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.hk_hold", rows, ["ts_code", "trade_date", "exchange"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockTransferSyncPayload(BaseModel):
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/transfer/sync")
def sync_stock_transfer(session: SessionDep, payload: StockTransferSyncPayload) -> Any:
    """同步转融资交易汇总"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync slb_len request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.trade_date:
            params["trade_date"] = payload.trade_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date

        logger.info(f"Fetching slb_len with params: {params}")
        df = pro.slb_len(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.slb_len", rows, ["trade_date"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockTopInstSyncPayload(BaseModel):
    trade_date: str  # 必填参数
    ts_code: str | None = None  # 可选参数


@router.post("/topinst/sync")
def sync_stock_top_inst(session: SessionDep, payload: StockTopInstSyncPayload) -> Any:
    """同步龙虎榜机构明细"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync top_inst request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {"trade_date": payload.trade_date}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code

        logger.info(f"Fetching top_inst with params: {params}")
        df = pro.top_inst(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.top_inst", rows, ["trade_date", "ts_code", "exalter", "side"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockStrongestSyncPayload(BaseModel):
    ts_code: str | None = None
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/strongest/sync")
def sync_stock_strongest(session: SessionDep, payload: StockStrongestSyncPayload) -> Any:
    """同步最强板块统计"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync limit_cpt_list request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.trade_date:
            params["trade_date"] = payload.trade_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date

        logger.info(f"Fetching limit_cpt_list with params: {params}")
        df = pro.limit_cpt_list(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.limit_cpt_list", rows, ["ts_code", "trade_date"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockThsConceptSyncPayload(BaseModel):
    ts_code: str | None = None
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/thsconcept/sync")
def sync_stock_ths_concept(session: SessionDep, payload: StockThsConceptSyncPayload) -> Any:
    """同步同花顺概念板块资金流向"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync moneyflow_cnt_ths request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.trade_date:
            params["trade_date"] = payload.trade_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date

        logger.info(f"Fetching moneyflow_cnt_ths with params: {params}")
        df = pro.moneyflow_cnt_ths(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.moneyflow_cnt_ths", rows, ["trade_date", "ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockThsIndustrySyncPayload(BaseModel):
    ts_code: str | None = None
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@router.post("/thsindustry/sync")
def sync_stock_ths_industry(session: SessionDep, payload: StockThsIndustrySyncPayload) -> Any:
    """同步同花顺行业资金流向"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync moneyflow_ind_ths request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.trade_date:
            params["trade_date"] = payload.trade_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date

        logger.info(f"Fetching moneyflow_ind_ths with params: {params}")
        df = pro.moneyflow_ind_ths(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.moneyflow_ind_ths", rows, ["trade_date", "ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


class StockDcConceptSyncPayload(BaseModel):
    ts_code: str | None = None
    trade_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    content_type: str | None = None


@router.post("/dcconcept/sync")
def sync_stock_dc_concept(session: SessionDep, payload: StockDcConceptSyncPayload) -> Any:
    """同步东财概念及行业板块资金流向"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync moneyflow_ind_dc request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.trade_date:
            params["trade_date"] = payload.trade_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        if payload.content_type:
            params["content_type"] = payload.content_type

        logger.info(f"Fetching moneyflow_ind_dc with params: {params}")
        df = pro.moneyflow_ind_dc(**params)

        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")

        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")

        succ, fail = _upsert_records(session, "stock.moneyflow_ind_dc", rows, ["trade_date", "ts_code", "content_type"])
        return {"message": "sync triggered", "success": succ, "failed": fail}

    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")

