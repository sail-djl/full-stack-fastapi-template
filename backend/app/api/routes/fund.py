from typing import Any
from fastapi import APIRouter
from app.api.deps import SessionDep
from app.services.fund_service import FundService

router = APIRouter(prefix="/fund", tags=["fund"])


@router.get("/basic")
def get_fund_basic(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    keyword: str | None = None,
    market: str | None = None,
    status: str | None = None,
    fund_type: str | None = None,
    management: str | None = None,
) -> Any:
    items, total = FundService.get_fund_basic_list(
        session=session,
        skip=skip,
        limit=limit,
        keyword=keyword,
        market=market,
        status=status,
        fund_type=fund_type,
        management=management,
    )
    return {"data": items, "count": total}

