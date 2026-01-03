from typing import Any, List
from fastapi import APIRouter, Query
from app.api.deps import SessionDep
from app.services.etf_service import EtfService

router = APIRouter(prefix="/etf", tags=["etf"])

@router.get("/basic")
def get_etf_basic(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    keyword: str | None = None,
    exchange: str | None = None,
    list_status: str | None = None,
    etf_type: str | None = None,
    mgr_name: str | None = None,
    index_codes: List[str] | None = Query(None, alias="index_codes[]"),
    ts_codes: List[str] | None = Query(None, alias="ts_codes[]"),
) -> Any:
    items, total = EtfService.get_etf_basic_list(
        session=session,
        skip=skip,
        limit=limit,
        keyword=keyword,
        exchange=exchange,
        list_status=list_status,
        etf_type=etf_type,
        mgr_name=mgr_name,
        index_codes=index_codes,
        ts_codes=ts_codes,
    )
    return {"data": items, "count": total}
