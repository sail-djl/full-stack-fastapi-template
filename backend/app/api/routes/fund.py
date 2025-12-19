import logging
import traceback
from typing import Any, Optional, List, Dict
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

# 数据库字段白名单 (fund_factor_pro)
FUND_FACTOR_PRO_COLUMNS = {
    "ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "change", "pct_change", "vol", "amount",
    "asi_bfq", "asit_bfq", "atr_bfq", "bbi_bfq", "bias1_bfq", "bias2_bfq", "bias3_bfq",
    "boll_lower_bfq", "boll_mid_bfq", "boll_upper_bfq", "brar_ar_bfq", "brar_br_bfq",
    "cci_bfq", "cr_bfq", "dfma_dif_bfq", "dfma_difma_bfq", "dmi_adx_bfq", "dmi_adxr_bfq", "dmi_mdi_bfq", "dmi_pdi_bfq",
    "downdays", "updays", "dpo_bfq", "madpo_bfq",
    "ema_bfq_5", "ema_bfq_10", "ema_bfq_20", "ema_bfq_30", "ema_bfq_60", "ema_bfq_90", "ema_bfq_250",
    "emv_bfq", "maemv_bfq", "expma_12_bfq", "expma_50_bfq",
    "kdj_bfq", "kdj_d_bfq", "kdj_k_bfq",
    "ktn_down_bfq", "ktn_mid_bfq", "ktn_upper_bfq",
    "lowdays", "topdays",
    "ma_bfq_5", "ma_bfq_10", "ma_bfq_20", "ma_bfq_30", "ma_bfq_60", "ma_bfq_90", "ma_bfq_250",
    "macd_bfq", "macd_dea_bfq", "macd_dif_bfq",
    "mass_bfq", "ma_mass_bfq", "mfi_bfq", "mtm_bfq", "mtmma_bfq", "obv_bfq",
    "psy_bfq", "psyma_bfq", "roc_bfq", "maroc_bfq",
    "rsi_bfq_6", "rsi_bfq_12", "rsi_bfq_24",
    "taq_down_bfq", "taq_mid_bfq", "taq_up_bfq",
    "trix_bfq", "trma_bfq", "vr_bfq", "wr_bfq", "wr1_bfq",
    "xsii_td1_bfq", "xsii_td2_bfq", "xsii_td3_bfq", "xsii_td4_bfq"
}



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


@router.get("/factor")
def get_fund_factor(
    session: SessionDep,
    ts_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """
    获取基金技术面因子数据
    """
    items = FundService.get_fund_factor_list(
        session=session,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


class FundSyncPayload(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    keyword: Optional[str] = None
    market: Optional[str] = None
    status: Optional[str] = None
    fund_type: Optional[str] = None
    management: Optional[str] = None


class FundFactorSyncPayload(BaseModel):
    ts_code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


def _to_yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)



def _get_last_factor_date(session: Session, ts_code: str) -> Optional[date]:
    sql = text("SELECT MAX(trade_date) AS last_date FROM fund.fund_factor_pro WHERE ts_code = :ts_code")
    with session.connection() as conn:
        row = conn.execute(sql, {"ts_code": ts_code}).fetchone()
        return row[0] if row and row[0] else None


def _upsert_factor_records(session: Session, records: List[dict]) -> tuple[int, int]:
    if not records:
        return 0, 0
    
    # 获取所有字段名 (基于第一条记录)
    first_keys = list(records[0].keys())
    
    # 过滤掉不属于表结构的字段
    keys = [k for k in first_keys if k in FUND_FACTOR_PRO_COLUMNS]
    
    if 'ts_code' not in keys or 'trade_date' not in keys:
        logger.error("Upsert factor failed: Missing primary keys (ts_code or trade_date)")
        return 0, len(records)

    # 简单的日期格式修正 (YYYYMMDD -> YYYY-MM-DD)
    processed_records = []
    for r in records:
        new_r = {k: r.get(k) for k in keys}
        # 处理 trade_date
        td = new_r.get('trade_date')
        if isinstance(td, str) and len(td) == 8:
             try:
                 new_r['trade_date'] = f"{td[:4]}-{td[4:6]}-{td[6:]}"
             except:
                 pass
        processed_records.append(new_r)
    
    records = processed_records

    # 构建 INSERT SQL
    cols = ", ".join(keys)
    vals = ", ".join([f":{k}" for k in keys])
    
    # 构建 UPDATE SET (排除主键)
    update_set = ", ".join([f"{k} = EXCLUDED.{k}" for k in keys if k not in ['ts_code', 'trade_date', 'id']])
    
    sql_str = f"""
        INSERT INTO fund.fund_factor_pro ({cols})
        VALUES ({vals})
        ON CONFLICT (ts_code, trade_date)
        DO UPDATE SET
            {update_set},
            update_time = CURRENT_TIMESTAMP
    """
    
    success = 0
    failed = 0
    
    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            session.execute(text(sql_str), batch)
            session.commit()
            success += len(batch)
        except Exception as e:
            logger.error(f"Upsert factor batch failed: {e}\\n{traceback.format_exc()}")
            session.rollback()
            # 降级为逐条插入以找出错误记录 (可选)
            for rec in batch:
                try:
                    session.execute(text(sql_str), rec)
                    session.commit()
                    success += 1
                except Exception as e2:
                    logger.error(f"Upsert factor single failed for {rec.get('ts_code')} {rec.get('trade_date')}: {e2}")
                    session.rollback()
                    failed += 1
                    
    return success, failed


@router.post("/factor/sync")
def sync_fund_factor(session: SessionDep, payload: FundFactorSyncPayload) -> Any:
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync factor request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    total_success = 0
    total_failed = 0

    # 1. 按代码同步
    if payload.ts_code:
        # 如果指定了代码，则同步该代码的历史数据
        # 确定时间范围
        start_d = None
        if payload.start_date:
            start_d = _parse_iso_date(payload.start_date)
        else:
            last_date = _get_last_factor_date(session, payload.ts_code)
            if last_date:
                start_d = last_date + timedelta(days=1)
            else:
                # 默认同步最近 3 年? 或者从 2005 开始?
                # 场内基金数据量不大，可以尝试同步较长历史，或者默认最近1年
                start_d = date.today() - timedelta(days=365*3)
        
        end_d = date.today()
        if payload.end_date:
            end_d = _parse_iso_date(payload.end_date)
            
        if start_d > end_d:
             return {"message": "No new data to sync", "success": 0, "failed": 0}

        # 分页获取 (虽然 fund_factor_pro 支持 start/end，但如果跨度太大可能会超时或受限)
        # 这里直接请求，Tushare Python SDK 会自动处理分页吗？不一定。
        # 安全起见，按年循环
        curr = start_d
        while curr <= end_d:
            next_year = curr + timedelta(days=365)
            # 结束日期不能超过 end_d
            batch_end = min(next_year, end_d)
            
            params = {
                "ts_code": payload.ts_code,
                "start_date": _to_yyyymmdd(curr),
                "end_date": _to_yyyymmdd(batch_end)
            }
            try:
                logger.info(f"Fetching fund_factor_pro for {payload.ts_code}, range: {params['start_date']} - {params['end_date']}")
                df = pro.fund_factor_pro(**params)
                
                if df is None:
                    logger.warning(f"Tushare returned None for {payload.ts_code}")
                elif df.empty:
                    logger.warning(f"Tushare returned empty DataFrame for {payload.ts_code}")
                else:
                    logger.info(f"Tushare returned {len(df)} records for {payload.ts_code}. Columns: {df.columns.tolist()}")

                if df is not None and not df.empty:
                    # 数据清洗
                    # 确保数值类型
                    numeric_cols = df.columns.drop(['ts_code', 'trade_date'])
                    for col in numeric_cols:
                         df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 将 NaN 转换为 None，以便存入数据库为 NULL
                    df = df.where(pd.notnull(df), None)

                    rows = df.to_dict("records")
                    succ, fail = _upsert_factor_records(session, rows)
                    total_success += succ
                    total_failed += fail
                else:
                    logger.info("No data found")
            except Exception as e:
                logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
                # 继续尝试下一段
            
            curr = batch_end + timedelta(days=1)

    # 2. 按日期范围同步 (所有场内基金)
    elif payload.start_date and payload.end_date:
        start_d = _parse_iso_date(payload.start_date)
        end_d = _parse_iso_date(payload.end_date)
        
        curr = start_d
        while curr <= end_d:
            trade_date_str = _to_yyyymmdd(curr)
            params = {"trade_date": trade_date_str}
            
            try:
                logger.info(f"Fetching fund_factor_pro for date {trade_date_str}")
                df = pro.fund_factor_pro(**params)

                if df is None:
                    logger.warning(f"Tushare returned None for date {trade_date_str}")
                elif df.empty:
                    logger.warning(f"Tushare returned empty DataFrame for date {trade_date_str}")
                else:
                    logger.info(f"Tushare returned {len(df)} records for date {trade_date_str}. Columns: {df.columns.tolist()}")

                if df is not None and not df.empty:
                    # 数据清洗
                    # 确保数值类型
                    numeric_cols = df.columns.drop(['ts_code', 'trade_date'])
                    for col in numeric_cols:
                         df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 将 NaN 转换为 None，以便存入数据库为 NULL
                    df = df.where(pd.notnull(df), None)

                    rows = df.to_dict("records")
                    succ, fail = _upsert_factor_records(session, rows)
                    total_success += succ
                    total_failed += fail
                else:
                    logger.info(f"No data found for {trade_date_str}")
            except Exception as e:
                import traceback
                logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
            
            curr += timedelta(days=1)
            
    else:
        raise HTTPException(status_code=400, detail="Must provide ts_code OR start_date/end_date")

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}



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
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    # 初始化 Tushare 接口
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync request received. Payload: {payload}")

    # 如果配置了自定义 API URL，则进行覆盖（针对代理/内网环境）
    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.keyword:
        raise HTTPException(status_code=400, detail="必须指定基金代码或名称")

    if not payload.start_date or not payload.end_date:
        raise HTTPException(status_code=400, detail="必须指定日期范围")

    total_success = 0
    total_failed = 0

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
    if not codes:
        return {"message": "未找到匹配的基金", "success": 0, "failed": 0}
    
    logger.info(f"Found {len(codes)} funds to sync.")

    start_d = _parse_iso_date(payload.start_date)
    end_d = _parse_iso_date(payload.end_date)
    start_date_str = _to_yyyymmdd(start_d)
    end_date_str = _to_yyyymmdd(end_d)

    for code in codes:
        try:
            params = {
                "ts_code": code,
                "start_date": start_date_str,
                "end_date": end_date_str
            }
            if payload.market in ("E", "O"):
                params["market"] = payload.market
                
            logger.info(f"Fetching fund_nav for {code}, range: {start_date_str}-{end_date_str}")
            df = pro.fund_nav(**params)
            
            if df is not None and not df.empty:
                logger.info(f"Tushare returned {len(df)} records for {code}")
                
                # -----------------------------------------------------------
                # 数据清洗与 pct_chg 计算 (参考 import_fund_nav_013286.py)
                # -----------------------------------------------------------
                
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

                # 转换 NaN 为 None
                df = df.where(pd.notnull(df), None)

                rows = df.to_dict("records")
                transformed = _transform_rows(rows)
                logger.info(f"-------------- Sync Data Batch ({len(transformed)}) for {code} --------------")
                
                if transformed:
                    succ, fail = _upsert_records(session, transformed)
                    total_success += succ
                    total_failed += fail
                    logger.info(f"Upsert Summary for {code}: Success={succ}, Failed={fail}")
                else:
                    logger.warning(f"No records left to upsert for {code} after filtering.")
                    
            else:
                logger.info(f"No data found for {code}")
                
        except Exception as e:
            logger.error(f"Sync failed for {code}: {e}")
            total_failed += 1 

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}
