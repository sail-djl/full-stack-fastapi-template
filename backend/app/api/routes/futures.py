import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.futures_service import FuturesService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/futures", tags=["futures"])

# ==================== Models ====================

class FuturesSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    exchange: str | None = None
    fut_code: str | None = None
    ts_code: str | None = None
    freq: str | None = None

# ==================== 期货合约信息 ====================

@router.get("/fut_basic")
def get_fut_basic_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    exchange: str | None = None,
    fut_type: str | None = None,
    fut_code: str | None = None,
    list_date: str | None = None,
) -> Any:
    """Get futures basic data list"""
    filters = {}
    if exchange:
        filters['exchange'] = exchange
    if fut_type:
        filters['fut_type'] = fut_type
    if fut_code:
        filters['fut_code'] = fut_code
    if list_date:
        filters['list_date'] = list_date
    
    return FuturesService.get_futures_list(
        session=session,
        table="futures.fut_basic",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="list_date DESC",
    )

@router.post("/fut_basic/sync")
def sync_fut_basic(session: SessionDep, payload: FuturesSyncPayload) -> Any:
    """Sync futures basic data from Tushare"""
    try:
        params = {}
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.fut_code:
            params["fut_code"] = payload.fut_code
        if payload.start_date:
            params["list_date"] = payload.start_date  # Tushare使用list_date作为开始日期参数
        
        return FuturesService.sync_from_tushare(
            session=session,
            table="futures.fut_basic",
            primary_keys=["ts_code"],
            tushare_api="fut_basic",
            params=params,
            date_columns=["list_date", "delist_date", "last_ddate"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== 交易日历 ====================

@router.get("/trade_cal")
def get_trade_cal_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    exchange: str | None = None,
    cal_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    is_open: int | None = None,
) -> Any:
    """Get trade calendar data list"""
    filters = {}
    if exchange:
        filters['exchange'] = exchange
    if cal_date:
        filters['cal_date'] = cal_date
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    if is_open is not None:
        filters['is_open'] = is_open
    
    return FuturesService.get_futures_list(
        session=session,
        table="futures.trade_cal",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="cal_date DESC",
    )

@router.post("/trade_cal/sync")
def sync_trade_cal(session: SessionDep, payload: FuturesSyncPayload) -> Any:
    """Sync trade calendar data from Tushare"""
    try:
        params = {}
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return FuturesService.sync_from_tushare(
            session=session,
            table="futures.trade_cal",
            primary_keys=["exchange", "cal_date"],
            tushare_api="trade_cal",
            params=params,
            date_columns=["cal_date", "pretrade_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== 期货日线行情 ====================

@router.get("/fut_daily")
def get_fut_daily_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    trade_date: str | None = None,
    exchange: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get futures daily data list"""
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if trade_date:
        filters['trade_date'] = trade_date
    if exchange:
        filters['exchange'] = exchange
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    
    return FuturesService.get_futures_list(
        session=session,
        table="futures.fut_daily",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="trade_date DESC",
    )

@router.post("/fut_daily/sync")
def sync_fut_daily(session: SessionDep, payload: FuturesSyncPayload) -> Any:
    """Sync futures daily data from Tushare"""
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return FuturesService.sync_from_tushare(
            session=session,
            table="futures.fut_daily",
            primary_keys=["ts_code", "trade_date"],
            tushare_api="fut_daily",
            params=params,
            date_columns=["trade_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== 期货周/月线行情 ====================

@router.get("/fut_weekly_monthly")
def get_fut_weekly_monthly_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    trade_date: str | None = None,
    freq: str | None = None,
    exchange: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get futures weekly/monthly data list"""
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if trade_date:
        filters['trade_date'] = trade_date
    if freq:
        filters['freq'] = freq
    if exchange:
        filters['exchange'] = exchange
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    
    return FuturesService.get_futures_list(
        session=session,
        table="futures.fut_weekly_monthly",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="trade_date DESC",
    )

@router.post("/fut_weekly_monthly/sync")
def sync_fut_weekly_monthly(session: SessionDep, payload: FuturesSyncPayload) -> Any:
    """Sync futures weekly/monthly data from Tushare"""
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.freq:
            params["freq"] = payload.freq
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return FuturesService.sync_from_tushare(
            session=session,
            table="futures.fut_weekly_monthly",
            primary_keys=["ts_code", "trade_date", "freq"],
            tushare_api="fut_weekly_monthly",
            params=params,
            date_columns=["trade_date", "end_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

