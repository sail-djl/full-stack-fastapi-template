import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.services.macro_service import MacroService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/macro", tags=["macro"])

# ==================== Models ====================

class MacroSyncPayload(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    start_m: str | None = None
    end_m: str | None = None
    start_q: str | None = None
    end_q: str | None = None

# ==================== GDP ====================

@router.get("/cn_gdp")
def get_macro_cn_gdp_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    quarter: str | None = None,
    start_q: str | None = None,
    end_q: str | None = None,
) -> Any:
    """Get GDP data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.gdp",
        skip=skip,
        limit=limit,
        date_col="quarter",
        date_filter=quarter,
        start_param=start_q,
        end_param=end_q,
    )

@router.post("/cn_gdp/sync")
def sync_macro_cn_gdp(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync GDP data from Tushare"""
    try:
        params = {}
        if payload.start_q:
            params["start_q"] = payload.start_q
        if payload.end_q:
            params["end_q"] = payload.end_q
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.gdp",
            primary_keys=["quarter"],
            tushare_api="cn_gdp",
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== CPI ====================

@router.get("/cpi")
def get_macro_cpi_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    month: str | None = None,
    start_m: str | None = None,
    end_m: str | None = None,
) -> Any:
    """Get CPI data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.cpi",
        skip=skip,
        limit=limit,
        date_col="month",
        date_filter=month,
        start_param=start_m,
        end_param=end_m,
    )

@router.post("/cpi/sync")
def sync_macro_cpi(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync CPI data from Tushare"""
    try:
        params = {}
        if payload.start_m:
            params["start_m"] = payload.start_m
        if payload.end_m:
            params["end_m"] = payload.end_m
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.cpi",
            primary_keys=["month"],
            tushare_api="cn_cpi",
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== PMI ====================

@router.get("/pmi")
def get_macro_pmi_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    month: str | None = None,
    start_m: str | None = None,
    end_m: str | None = None,
) -> Any:
    """Get PMI data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.pmi",
        skip=skip,
        limit=limit,
        date_col="month",
        date_filter=month,
        start_param=start_m,
        end_param=end_m,
    )

@router.post("/pmi/sync")
def sync_macro_pmi(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync PMI data from Tushare"""
    try:
        params = {}
        if payload.start_m:
            params["start_m"] = payload.start_m
        if payload.end_m:
            params["end_m"] = payload.end_m
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.pmi",
            primary_keys=["month"],
            tushare_api="cn_pmi",
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== PPI ====================

@router.get("/ppi")
def get_macro_ppi_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    month: str | None = None,
    start_m: str | None = None,
    end_m: str | None = None,
) -> Any:
    """Get PPI data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.ppi",
        skip=skip,
        limit=limit,
        date_col="month",
        date_filter=month,
        start_param=start_m,
        end_param=end_m,
    )

@router.post("/ppi/sync")
def sync_macro_ppi(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync PPI data from Tushare"""
    try:
        params = {}
        if payload.start_m:
            params["start_m"] = payload.start_m
        if payload.end_m:
            params["end_m"] = payload.end_m
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.ppi",
            primary_keys=["month"],
            tushare_api="cn_ppi",
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== Shibor ====================

@router.get("/shibor")
def get_macro_shibor_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get Shibor data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.shibor",
        skip=skip,
        limit=limit,
        date_col="date",
        date_filter=date,
        start_param=start_date,
        end_param=end_date,
    )

@router.post("/shibor/sync")
def sync_macro_shibor(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync Shibor data from Tushare"""
    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        # Tushare 字段名到数据库字段名的映射
        field_mapping = {
            "on": "on_rate",
            "1w": "rate_1w",
            "2w": "rate_2w",
            "1m": "rate_1m",
            "3m": "rate_3m",
            "6m": "rate_6m",
            "9m": "rate_9m",
            "1y": "rate_1y",
        }
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.shibor",
            primary_keys=["date"],
            tushare_api="shibor",
            params=params,
            date_column="date",
            field_mapping=field_mapping,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== LPR ====================

@router.get("/lpr")
def get_macro_lpr_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get LPR data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.lpr",
        skip=skip,
        limit=limit,
        date_col="date",
        date_filter=date,
        start_param=start_date,
        end_param=end_date,
    )

@router.post("/lpr/sync")
def sync_macro_lpr(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync LPR data from Tushare"""
    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        # Tushare 字段名到数据库字段名的映射
        field_mapping = {
            "1y": "rate_1y",
            "5y": "rate_5y",
        }
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.lpr",
            primary_keys=["date"],
            tushare_api="shibor_lpr",
            params=params,
            date_column="date",
            field_mapping=field_mapping,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== Money Supply ====================

@router.get("/money_supply")
def get_macro_money_supply_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    month: str | None = None,
    start_m: str | None = None,
    end_m: str | None = None,
) -> Any:
    """Get Money Supply data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.money_supply",
        skip=skip,
        limit=limit,
        date_col="month",
        date_filter=month,
        start_param=start_m,
        end_param=end_m,
    )

@router.post("/money_supply/sync")
def sync_macro_money_supply(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync Money Supply data from Tushare"""
    try:
        params = {}
        if payload.start_m:
            params["start_m"] = payload.start_m
        if payload.end_m:
            params["end_m"] = payload.end_m
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.money_supply",
            primary_keys=["month"],
            tushare_api="cn_m",
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== Social Financing ====================

@router.get("/social_financing")
def get_macro_social_financing_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    month: str | None = None,
    start_m: str | None = None,
    end_m: str | None = None,
) -> Any:
    """Get Social Financing data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.social_financing",
        skip=skip,
        limit=limit,
        date_col="month",
        date_filter=month,
        start_param=start_m,
        end_param=end_m,
    )

@router.post("/social_financing/sync")
def sync_macro_social_financing(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync Social Financing data from Tushare"""
    try:
        params = {}
        if payload.start_m:
            params["start_m"] = payload.start_m
        if payload.end_m:
            params["end_m"] = payload.end_m
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.social_financing",
            primary_keys=["month"],
            tushare_api="sf_month",
            params=params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== US Treasury Yield Curve ====================

@router.get("/us_treasury_yield_curve")
def get_macro_us_treasury_yield_curve_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get US Treasury Yield Curve data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.us_treasury_yield_curve",
        skip=skip,
        limit=limit,
        date_col="date",
        date_filter=date,
        start_param=start_date,
        end_param=end_date,
    )

@router.post("/us_treasury_yield_curve/sync")
def sync_macro_us_treasury_yield_curve(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync US Treasury Yield Curve data from Tushare"""
    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.us_treasury_yield_curve",
            primary_keys=["date"],
            tushare_api="us_tycr",
            params=params,
            date_column="date",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== US Treasury Real Yield Curve ====================

@router.get("/us_treasury_real_yield_curve")
def get_macro_us_treasury_real_yield_curve_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get US Treasury Real Yield Curve data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.us_treasury_real_yield_curve",
        skip=skip,
        limit=limit,
        date_col="date",
        date_filter=date,
        start_param=start_date,
        end_param=end_date,
    )

@router.post("/us_treasury_real_yield_curve/sync")
def sync_macro_us_treasury_real_yield_curve(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync US Treasury Real Yield Curve data from Tushare"""
    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.us_treasury_real_yield_curve",
            primary_keys=["date"],
            tushare_api="us_trycr",
            params=params,
            date_column="date",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== US Treasury Bill ====================

@router.get("/us_treasury_bill")
def get_macro_us_treasury_bill_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get US Treasury Bill data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.us_treasury_bill",
        skip=skip,
        limit=limit,
        date_col="date",
        date_filter=date,
        start_param=start_date,
        end_param=end_date,
    )

@router.post("/us_treasury_bill/sync")
def sync_macro_us_treasury_bill(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync US Treasury Bill data from Tushare"""
    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.us_treasury_bill",
            primary_keys=["date"],
            tushare_api="us_tbr",
            params=params,
            date_column="date",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== US Treasury Long Term ====================

@router.get("/us_treasury_long_term")
def get_macro_us_treasury_long_term_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get US Treasury Long Term data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.us_treasury_long_term",
        skip=skip,
        limit=limit,
        date_col="date",
        date_filter=date,
        start_param=start_date,
        end_param=end_date,
    )

@router.post("/us_treasury_long_term/sync")
def sync_macro_us_treasury_long_term(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync US Treasury Long Term data from Tushare"""
    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.us_treasury_long_term",
            primary_keys=["date"],
            tushare_api="us_tltr",
            params=params,
            date_column="date",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")

# ==================== US Treasury Real Long Term Avg ====================

@router.get("/us_treasury_real_long_term_avg")
def get_macro_us_treasury_real_long_term_avg_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    """Get US Treasury Real Long Term Avg data list"""
    return MacroService.get_macro_list(
        session=session,
        table="macro.us_treasury_real_long_term_avg",
        skip=skip,
        limit=limit,
        date_col="date",
        date_filter=date,
        start_param=start_date,
        end_param=end_date,
    )

@router.post("/us_treasury_real_long_term_avg/sync")
def sync_macro_us_treasury_real_long_term_avg(session: SessionDep, payload: MacroSyncPayload) -> Any:
    """Sync US Treasury Real Long Term Avg data from Tushare"""
    try:
        params = {}
        if payload.start_date:
            params["start_date"] = payload.start_date
        if payload.end_date:
            params["end_date"] = payload.end_date
        
        return MacroService.sync_from_tushare(
            session=session,
            table="macro.us_treasury_real_long_term_avg",
            primary_keys=["date"],
            tushare_api="us_trltr",
            params=params,
            date_column="date",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")
