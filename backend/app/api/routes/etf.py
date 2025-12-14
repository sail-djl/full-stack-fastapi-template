from typing import Any
from fastapi import APIRouter
from app.api.deps import SessionDep
from app.services.fund_service import FundService

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
) -> Any:
    items, total = FundService.get_etf_basic_list(
        session=session,
        skip=skip,
        limit=limit,
        keyword=keyword,
        exchange=exchange,
        list_status=list_status,
        etf_type=etf_type,
        mgr_name=mgr_name,
    )
    return {"data": items, "count": total}
