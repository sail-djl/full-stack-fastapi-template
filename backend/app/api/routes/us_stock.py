import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.us_stock_service import UsStockService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/us_stock", tags=["us_stock"])

class UsStockSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    ts_code: str | None = None
    classify: str | None = None

@router.get("/us_basic")
def get_us_basic_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    classify: str | None = None,
) -> Any:
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if classify:
        filters['classify'] = classify
    
    return UsStockService.get_us_stock_list(
        session=session,
        table="us_stock.us_basic",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="list_date DESC",
    )

@router.post("/us_basic/sync")
def sync_us_basic(session: SessionDep, payload: UsStockSyncPayload) -> Any:
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.classify:
            params["classify"] = payload.classify
        
        return UsStockService.sync_from_tushare(
            session=session,
            table="us_stock.us_basic",
            primary_keys=["ts_code"],
            tushare_api="us_basic",
            params=params,
            date_columns=["list_date", "delist_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

@router.get("/us_daily")
def get_us_daily_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
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
    
    return UsStockService.get_us_stock_list(
        session=session,
        table="us_stock.us_daily",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="trade_date DESC",
    )

@router.post("/us_daily/sync")
def sync_us_daily(session: SessionDep, payload: UsStockSyncPayload) -> Any:
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return UsStockService.sync_from_tushare(
            session=session,
            table="us_stock.us_daily",
            primary_keys=["ts_code", "trade_date"],
            tushare_api="us_daily",
            params=params,
            date_columns=["trade_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

