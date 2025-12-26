import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.option_service import OptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/option", tags=["option"])

# ==================== Models ====================

class OptionSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    ts_code: str | None = None
    exchange: str | None = None
    opt_code: str | None = None
    call_put: str | None = None
    list_date: str | None = None

# ==================== 期权合约信息 ====================

@router.get("/opt_basic")
def get_opt_basic_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    exchange: str | None = None,
    list_date: str | None = None,
    opt_code: str | None = None,
    call_put: str | None = None,
) -> Any:
    """Get option basic data list"""
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if exchange:
        filters['exchange'] = exchange
    if list_date:
        filters['list_date'] = list_date
    if opt_code:
        filters['opt_code'] = opt_code
    if call_put:
        filters['call_put'] = call_put
    
    return OptionService.get_option_list(
        session=session,
        table="option.opt_basic",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="list_date DESC",
    )

@router.post("/opt_basic/sync")
def sync_opt_basic(session: SessionDep, payload: OptionSyncPayload) -> Any:
    """Sync option basic data from Tushare"""
    try:
        params = {}
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.opt_code:
            params["opt_code"] = payload.opt_code
        if payload.call_put:
            params["call_put"] = payload.call_put
        if payload.list_date:
            params["list_date"] = payload.list_date
        
        return OptionService.sync_from_tushare(
            session=session,
            table="option.opt_basic",
            primary_keys=["ts_code"],
            tushare_api="opt_basic",
            params=params,
            date_columns=["list_date", "delist_date", "maturity_date", "last_edate", "last_ddate"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== 期权日线行情 ====================

@router.get("/opt_daily")
def get_opt_daily_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    exchange: str | None = None,
) -> Any:
    """Get option daily data list"""
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if trade_date:
        filters['trade_date'] = trade_date
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    if exchange:
        filters['exchange'] = exchange
    
    return OptionService.get_option_list(
        session=session,
        table="option.opt_daily",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="trade_date DESC",
    )

@router.post("/opt_daily/sync")
def sync_opt_daily(session: SessionDep, payload: OptionSyncPayload) -> Any:
    """Sync option daily data from Tushare"""
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
        
        return OptionService.sync_from_tushare(
            session=session,
            table="option.opt_daily",
            primary_keys=["ts_code", "trade_date"],
            tushare_api="opt_daily",
            params=params,
            date_columns=["trade_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

