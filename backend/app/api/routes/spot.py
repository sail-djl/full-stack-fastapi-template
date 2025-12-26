import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.spot_service import SpotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spot", tags=["spot"])

# ==================== Models ====================

class SpotSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    ts_code: str | None = None

# ==================== 黄金现货基础信息 ====================

@router.get("/sge_basic")
def get_sge_basic_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
) -> Any:
    """Get spot basic data list"""
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    
    return SpotService.get_spot_list(
        session=session,
        table="spot.sge_basic",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="list_date DESC",
    )

@router.post("/sge_basic/sync")
def sync_sge_basic(session: SessionDep, payload: SpotSyncPayload) -> Any:
    """Sync spot basic data from Tushare"""
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        
        return SpotService.sync_from_tushare(
            session=session,
            table="spot.sge_basic",
            primary_keys=["ts_code"],
            tushare_api="sge_basic",
            params=params,
            date_columns=["list_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== 上海黄金现货日行情 ====================

@router.get("/sge_daily")
def get_sge_daily_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get spot daily data list"""
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if trade_date:
        filters['trade_date'] = trade_date
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    
    return SpotService.get_spot_list(
        session=session,
        table="spot.sge_daily",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="trade_date DESC",
    )

@router.post("/sge_daily/sync")
def sync_sge_daily(session: SessionDep, payload: SpotSyncPayload) -> Any:
    """Sync spot daily data from Tushare"""
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return SpotService.sync_from_tushare(
            session=session,
            table="spot.sge_daily",
            primary_keys=["ts_code", "trade_date"],
            tushare_api="sge_daily",
            params=params,
            date_columns=["trade_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

