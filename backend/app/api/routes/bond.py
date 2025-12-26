import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.bond_service import BondService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bond", tags=["bond"])

class BondSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    ts_code: str | None = None
    list_date: str | None = None
    exchange: str | None = None
    ann_date: str | None = None

@router.get("/cb_basic")
def get_cb_basic_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    list_date: str | None = None,
    exchange: str | None = None,
) -> Any:
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if list_date:
        filters['list_date'] = list_date
    if exchange:
        filters['exchange'] = exchange
    
    return BondService.get_bond_list(
        session=session,
        table="bond.cb_basic",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="list_date DESC",
    )

@router.post("/cb_basic/sync")
def sync_cb_basic(session: SessionDep, payload: BondSyncPayload) -> Any:
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.exchange:
            params["exchange"] = payload.exchange
        if payload.list_date:
            params["list_date"] = payload.list_date
        
        return BondService.sync_from_tushare(
            session=session,
            table="bond.cb_basic",
            primary_keys=["ts_code"],
            tushare_api="cb_basic",
            params=params,
            date_columns=["value_date", "maturity_date", "list_date", "delist_date", "conv_start_date", "conv_end_date", "conv_stop_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

@router.get("/cb_issue")
def get_cb_issue_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    ts_code: str | None = None,
    ann_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    filters = {}
    if ts_code:
        filters['ts_code'] = ts_code
    if ann_date:
        filters['ann_date'] = ann_date
    if start_date:
        filters['start_date'] = start_date
    if end_date:
        filters['end_date'] = end_date
    
    return BondService.get_bond_list(
        session=session,
        table="bond.cb_issue",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="ann_date DESC",
    )

@router.post("/cb_issue/sync")
def sync_cb_issue(session: SessionDep, payload: BondSyncPayload) -> Any:
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.ann_date:
            params["ann_date"] = payload.ann_date
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return BondService.sync_from_tushare(
            session=session,
            table="bond.cb_issue",
            primary_keys=["ts_code", "ann_date"],
            tushare_api="cb_issue",
            params=params,
            date_columns=["ann_date", "res_ann_date", "onl_date", "shd_ration_date", "shd_ration_record_date", "shd_ration_pay_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

@router.get("/cb_daily")
def get_cb_daily_list(
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
    
    return BondService.get_bond_list(
        session=session,
        table="bond.cb_daily",
        skip=skip,
        limit=limit,
        filters=filters,
        order_by="trade_date DESC",
    )

@router.post("/cb_daily/sync")
def sync_cb_daily(session: SessionDep, payload: BondSyncPayload) -> Any:
    try:
        params = {}
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return BondService.sync_from_tushare(
            session=session,
            table="bond.cb_daily",
            primary_keys=["ts_code", "trade_date"],
            tushare_api="cb_daily",
            params=params,
            date_columns=["trade_date"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

