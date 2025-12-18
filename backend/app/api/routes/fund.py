import logging
from typing import Any, Optional, List
from datetime import datetime, timedelta, date

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session
from app.api.deps import SessionDep
from app.services.fund_service import FundService
from app.core.config import settings

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


class FundSyncPayload(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    keyword: Optional[str] = None
    market: Optional[str] = None
    status: Optional[str] = None
    fund_type: Optional[str] = None
    management: Optional[str] = None


def _to_yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)


def _get_last_nav_date(session: Session, ts_code: str) -> Optional[date]:
    sql = text("SELECT MAX(nav_date) AS last_date FROM fund.fund_nav WHERE ts_code = :ts_code")
    with session.connection() as conn:
        row = conn.execute(sql, {"ts_code": ts_code}).fetchone()
        return row[0] if row and row[0] else None


def _upsert_records(session: Session, records: List[dict]) -> tuple[int, int]:
    success = 0
    failed = 0
    sql = text(
        """
        INSERT INTO fund.fund_nav (
            ts_code, nav_date, ann_date, unit_nav, accum_nav,
            accum_div, adj_nav, pct_chg, net_asset, total_netasset
        ) VALUES (
            :ts_code, :nav_date, :ann_date, :unit_nav, :accum_nav,
            :accum_div, :adj_nav, :pct_chg, :net_asset, :total_netasset
        )
        ON CONFLICT (ts_code, nav_date)
        DO UPDATE SET
            ann_date = EXCLUDED.ann_date,
            unit_nav = EXCLUDED.unit_nav,
            accum_nav = EXCLUDED.accum_nav,
            accum_div = EXCLUDED.accum_div,
            adj_nav = EXCLUDED.adj_nav,
            pct_chg = EXCLUDED.pct_chg,
            net_asset = EXCLUDED.net_asset,
            total_netasset = EXCLUDED.total_netasset,
            update_time = CURRENT_TIMESTAMP
        """
    )
    for rec in records:
        try:
            session.execute(sql, rec)
            session.commit()
            success += 1
        except Exception as e:
            logger.error(f"Upsert failed for {rec.get('ts_code')} {rec.get('nav_date')}: {e}")
            session.rollback()
            failed += 1
    return success, failed


def _transform_rows(rows: List[dict]) -> List[dict]:
    out: List[dict] = []
    for r in rows:
        nav_date = r.get("nav_date")
        ann_date = r.get("ann_date")
        def _to_date(val: Optional[str]) -> Optional[date]:
            if not val:
                return None
            try:
                return datetime.strptime(val, "%Y%m%d").date()
            except Exception:
                return None
        def _to_num(val: Any) -> Optional[float]:
            try:
                if val is None or val == "":
                    return None
                return float(val)
            except Exception:
                return None
        out.append(
            {
                "ts_code": r.get("ts_code"),
                "nav_date": _to_date(nav_date),
                "ann_date": _to_date(ann_date),
                "unit_nav": _to_num(r.get("unit_nav")),
                "accum_nav": _to_num(r.get("accum_nav")),
                "accum_div": _to_num(r.get("accum_div")),
                "adj_nav": _to_num(r.get("adj_nav")),
                "pct_chg": _to_num(r.get("pct_chg")),
                "net_asset": _to_num(r.get("net_asset")),
                "total_netasset": _to_num(r.get("total_netasset")),
            }
        )
    return out


@router.post("/nav/sync")
def sync_fund_nav(session: SessionDep, payload: FundSyncPayload) -> Any:
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    # 初始化 Tushare 接口
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync request received. Payload: {payload}")

    # 如果配置了自定义 API URL，则进行覆盖（针对代理/内网环境）
    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    total_success = 0
    total_failed = 0
    if payload.start_date or payload.end_date:
        if payload.start_date and not payload.end_date:
            payload.end_date = payload.start_date
        if payload.end_date and not payload.start_date:
            payload.start_date = payload.end_date

        if not payload.start_date or not payload.end_date:
            raise HTTPException(status_code=400, detail="start_date 和 end_date 需同时提供")

        start_d = _parse_iso_date(payload.start_date)
        end_d = _parse_iso_date(payload.end_date)
        codes: List[str] = []
        items, _ = FundService.get_fund_basic_list(
            session=session,
            skip=0,
            limit=100000,
            keyword=payload.keyword,
            market=payload.market,
            status=payload.status,
            fund_type=payload.fund_type,
            management=payload.management,
        )
        if items:
            codes = [it["ts_code"] for it in items if it.get("ts_code")]
        cur = start_d
        while cur <= end_d:
            params: dict[str, Any] = {"nav_date": _to_yyyymmdd(cur)}
            if payload.market in ("E", "O"):
                params["market"] = payload.market
            
            try:
                logger.info(f"Fetching fund_nav for date {cur}, params: {params}")
                df = pro.fund_nav(**params)
            except Exception as e:
                # 记录失败但不中断整个循环，或者选择中断
                # 这里我们选择中断并返回错误，因为Token问题通常是全局的
                raise HTTPException(status_code=500, detail=f"Tushare API 调用失败: {e}")

            if df is not None and not df.empty:
                # -----------------------------------------------------------
                # 数据清洗与 pct_chg 计算 (参考 import_fund_nav_013286.py)
                # -----------------------------------------------------------
                import pandas as pd
                
                # 1. 确保 unit_nav 是数值型
                if 'unit_nav' in df.columns:
                    df['unit_nav'] = pd.to_numeric(df['unit_nav'], errors='coerce')
                
                # 2. 按代码和日期排序 (日期为 YYYYMMDD 字符串，排序有效)
                if 'ts_code' in df.columns and 'nav_date' in df.columns:
                    df = df.sort_values(['ts_code', 'nav_date'])
                
                # 3. 计算 pct_chg
                if 'unit_nav' in df.columns and 'ts_code' in df.columns:
                    # 计算新的涨跌幅
                    calculated_pct = df.groupby('ts_code')['unit_nav'].pct_change() * 100
                    
                    # 如果原数据中有 pct_chg，则优先使用计算值，但保留计算值为 NaN (第一条) 时的原值
                    if 'pct_chg' in df.columns:
                         # 确保原 pct_chg 也是数值
                         df['pct_chg'] = pd.to_numeric(df['pct_chg'], errors='coerce')
                         df['pct_chg'] = calculated_pct.fillna(df['pct_chg'])
                    else:
                         df['pct_chg'] = calculated_pct
                # -----------------------------------------------------------

                rows = df.to_dict("records")
                if codes:
                    rows = [r for r in rows if r.get("ts_code") in codes]
                transformed = _transform_rows(rows)
                logger.info(f"-------------- Sync Data Batch ({len(transformed)}) --------------")
                for item in transformed:
                    logger.info(item)
                logger.info("---------------------------------------------------------------")
                succ, fail = _upsert_records(session, transformed)
                total_success += succ
                total_failed += fail
            else:
                logger.info(f"No data found for date {cur}")
            cur += timedelta(days=1)
    else:
        items, _ = FundService.get_fund_basic_list(
            session=session,
            skip=0,
            limit=100000,
            keyword=payload.keyword,
            market=payload.market,
            status=payload.status,
            fund_type=payload.fund_type,
            management=payload.management,
        )
        codes = [it["ts_code"] for it in items if it.get("ts_code")]
        for code in codes:
            last = _get_last_nav_date(session, code)
            start_d = last + timedelta(days=1) if last else None
            params: dict[str, Any] = {"ts_code": code}
            if start_d:
                params["start_date"] = _to_yyyymmdd(start_d)
            df = pro.fund_nav(**params)
            if df is not None and not df.empty:
                rows = df.to_dict("records")
                transformed = _transform_rows(rows)
                logger.info(f"-------------- Sync Data Batch ({len(transformed)}) for {code} --------------")
                for item in transformed:
                    logger.info(item)
                logger.info("---------------------------------------------------------------")
                succ, fail = _upsert_records(session, transformed)
                total_success += succ
                total_failed += fail
            else:
                logger.info(f"No data found for code {code}")
    return {"message": "sync triggered", "success": total_success, "failed": total_failed}
