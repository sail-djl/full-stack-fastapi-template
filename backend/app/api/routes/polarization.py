from typing import Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.deps import SessionDep
from app.models import (
    PolarizationPublic,
    PolarizationCreate,
    PolarizationUpdate,
    DeviationPublic,
    DeviationCreate,
    DeviationsPublic,
)
from app.services.polarization_service import PolarizationService, DeviationService
from app.services.fund_service import FundService

router = APIRouter(prefix="/polarization", tags=["polarization"])


# ============================================
# Fund List (基金列表) 路由 - 从 fund.fund_basic 和 fund.fund_nav 查询
# ============================================
@router.get("/fund-list")
def get_fund_list(
    session: SessionDep,
) -> Any:
    """
    获取基金列表（包含最新净值信息）
    数据来源: fund.fund_basic 和 fund.fund_nav
    """
    funds = FundService.get_fund_list(session=session)
    # 调试：检查 001593.OF 的数据
    fund_001593 = next((f for f in funds if f.get('code') == '001593.OF'), None)
    if fund_001593:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Backend: 001593.OF data: {fund_001593}")
        logger.info(f"🔍 Backend: changePercent={fund_001593.get('changePercent')}, type={type(fund_001593.get('changePercent'))}")
        logger.info(f"🔍 Backend: price={fund_001593.get('price')}, type={type(fund_001593.get('price'))}")
    return funds


# ============================================
# Deviation (偏差数据) 路由 - 从 fund.fund_nav 计算
# ============================================
@router.get("/deviation")
def get_deviation(
    session: SessionDep,
    fund1Code: str = Query(..., alias="fund1Code", description="基金1代码"),
    fund2Code: str = Query(..., alias="fund2Code", description="基金2代码"),
    timeRange: int = Query(7, alias="timeRange", description="时间范围（天数）"),
) -> Any:
    """
    获取偏差数据（从 fund.fund_nav 计算）
    数据来源: fund.fund_nav
    """
    deviations = FundService.get_deviation_data(
        session=session,
        fund1_code=fund1Code,
        fund2_code=fund2Code,
        time_range=timeRange,
    )
    return deviations


@router.get("/deviation-summary")
def get_deviation_summary(
    session: SessionDep,
    fund1Code: str = Query(..., alias="fund1Code", description="基金1代码"),
    fund2Code: str = Query(..., alias="fund2Code", description="基金2代码"),
) -> Any:
    """
    获取偏差摘要（今日、周、月、年平均偏差）
    数据来源: fund.fund_nav
    """
    summary = FundService.get_deviation_summary(
        session=session,
        fund1_code=fund1Code,
        fund2_code=fund2Code,
    )
    return summary


# ============================================
# Polarization (偏振度) 路由 - 从 fund.fund_nav 计算
# ============================================
@router.get("/polarization")
def get_polarization_from_db(
    session: SessionDep,
    fund1Code: str = Query(..., alias="fund1Code", description="基金1代码"),
    fund2Code: str = Query(..., alias="fund2Code", description="基金2代码"),
) -> Any:
    """
    获取偏振度数据（从 fund.fund_nav 计算）
    数据来源: fund.fund_nav
    """
    polarization = FundService.get_polarization_data(
        session=session,
        fund1_code=fund1Code,
        fund2_code=fund2Code,
    )
    return polarization


# ============================================
# Polarization (偏振度) 路由 - 原有接口（从 polarization 表查询）
# ============================================
@router.get("/polarization-stored", response_model=PolarizationPublic)
def get_polarization_stored(
    session: SessionDep,
    etf1_code: str = Query(..., description="ETF1代码"),
    etf2_code: str = Query(..., description="ETF2代码"),
) -> Any:
    """
    获取偏振度数据（从 polarization 表查询，已存储的计算结果）
    """
    polarization = PolarizationService.get_polarization(
        session=session, etf1_code=etf1_code, etf2_code=etf2_code
    )
    if not polarization:
        raise HTTPException(status_code=404, detail="Polarization data not found")
    return PolarizationPublic.model_validate(polarization)


@router.post("/", response_model=PolarizationPublic)
def create_or_update_polarization(
    *,
    session: SessionDep,
    polarization_in: PolarizationCreate,
) -> Any:
    """
    创建或更新偏振度数据
    """
    polarization = PolarizationService.create_or_update_polarization(
        session=session, polarization_in=polarization_in
    )
    return PolarizationPublic.model_validate(polarization)


# ============================================
# Deviation (偏差数据) 路由 - 原有接口（从 deviation 表查询）
# ============================================
@router.get("/deviations-stored", response_model=DeviationsPublic)
def get_deviations_stored(
    session: SessionDep,
    etf1_code: str = Query(..., description="ETF1代码"),
    etf2_code: str = Query(..., description="ETF2代码"),
    time_range: int = Query(7, description="时间范围（天数）"),
) -> Any:
    """
    获取偏差数据（从 deviation 表查询，已存储的计算结果）
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=time_range)
    
    deviations, count = DeviationService.get_deviations(
        session=session,
        etf1_code=etf1_code,
        etf2_code=etf2_code,
        start_date=start_date,
        end_date=end_date,
    )
    
    return DeviationsPublic(
        data=[DeviationPublic.model_validate(d) for d in deviations],
        count=count
    )


@router.post("/deviations", response_model=DeviationPublic)
def create_deviation(
    *,
    session: SessionDep,
    deviation_in: DeviationCreate,
) -> Any:
    """
    创建偏差数据
    """
    deviation = DeviationService.create_deviation(
        session=session, deviation_in=deviation_in
    )
    return DeviationPublic.model_validate(deviation)

