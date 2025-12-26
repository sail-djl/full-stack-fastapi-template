import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.forex_service import ForexService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forex", tags=["forex"])

class ForexSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    ts_code: str | None = None
    exchange: str | None = None
    classify: str | None = None

@router.get("/fx_obasic")
def get_fx_obasic_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    exchange: str | None = None,
    classify: str | None = None,
) -> Any:
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if exchange:
        filters['exchange'] = exchange
    if classify:
        filters['classify'] = classify
    
    return ForexService.get_forex_list(
        session=session,
        table="forex.fx_obasic",
        skip=skip,
        limit=limit,
        filters=filters,
    )

@router.post("/fx_obasic/sync")
def sync_fx_obasic(session: SessionDep, payload: ForexSyncPayload) -> Any:
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.classify:
            params["classify"] = payload.classify
        
        return ForexService.sync_from_tushare(
            session=session,
            table="forex.fx_obasic",
            primary_keys=["ts_code"],
            tushare_api="fx_obasic",
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

@router.get("/fx_daily")
def get_fx_daily_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    exchange: str | None = None,
) -> Any:
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
    
    return ForexService.get_forex_list(
        session=session,
        table="forex.fx_daily",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="trade_date DESC",
    )

@router.post("/fx_daily/sync")
def sync_fx_daily(session: SessionDep, payload: ForexSyncPayload) -> Any:
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
        
        return ForexService.sync_from_tushare(
            session=session,
            table="forex.fx_daily",
            primary_keys=["ts_code", "trade_date"],
            tushare_api="fx_daily",
            params=params,
            date_columns=["trade_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

