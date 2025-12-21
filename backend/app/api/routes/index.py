import logging
import traceback
from typing import Any, Optional, List
from datetime import timedelta, date

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session
from app.api.deps import SessionDep
from app.services.index_service import IndexService
from app.core.config import settings

router = APIRouter(prefix="/index", tags=["index"])


# ==================== 列表查询接口 ====================

@router.get("/basic")
def get_index_basic(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    keyword: str | None = None,
    market: str | None = None,
    publisher: str | None = None,
    category: str | None = None,
) -> Any:
    """获取指数基础信息列表"""
    items, total = IndexService.get_index_basic_list(
        session=session,
        skip=skip,
        limit=limit,
        keyword=keyword,
        market=market,
        publisher=publisher,
        category=category,
    )
    return {"data": items, "count": total}


@router.get("/daily")
def get_index_daily(
    session: SessionDep,
    ts_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """
    获取指数日线行情列表
    支持单个 ts_code 或多个 ts_code（逗号分隔，如：000001.SH,399001.SZ）
    """
    items = IndexService.get_index_daily_list(
        session=session,
        ts_code=ts_code,  # 支持逗号分隔的字符串
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


@router.get("/dailybasic")
def get_index_dailybasic(
    session: SessionDep,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """获取大盘指数每日指标列表"""
    items = IndexService.get_index_dailybasic_list(
        session=session,
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


@router.get("/weekly")
def get_index_weekly(
    session: SessionDep,
    ts_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """获取指数周线行情列表"""
    items = IndexService.get_index_weekly_list(
        session=session,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


@router.get("/classify")
def get_index_classify(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    index_code: str | None = None,
    level: str | None = None,
    parent_code: str | None = None,
    src: str = "SW2021",
    keyword: str | None = None,
) -> Any:
    """获取申万行业分类列表"""
    items, total = IndexService.get_index_classify_list(
        session=session,
        skip=skip,
        limit=limit,
        index_code=index_code,
        level=level,
        parent_code=parent_code,
        src=src,
        keyword=keyword,
    )
    return {"data": items, "count": total}


@router.get("/member")
def get_index_member(
    session: SessionDep,
    skip: int = 0,
    limit: int = 1000,
    l1_code: str | None = None,
    l2_code: str | None = None,
    l3_code: str | None = None,
    ts_code: str | None = None,
    is_new: str = "Y",
) -> Any:
    """获取申万行业成分构成列表"""
    items, total = IndexService.get_index_member_all_list(
        session=session,
        skip=skip,
        limit=limit,
        l1_code=l1_code,
        l2_code=l2_code,
        l3_code=l3_code,
        ts_code=ts_code,
        is_new=is_new,
    )
    return {"data": items, "count": total}


@router.get("/sw/daily")
def get_sw_daily(
    session: SessionDep,
    ts_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """获取申万行业日线行情列表"""
    items = IndexService.get_sw_daily_list(
        session=session,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


@router.get("/global")
def get_index_global(
    session: SessionDep,
    ts_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """获取国际指数列表"""
    items = IndexService.get_index_global_list(
        session=session,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


@router.get("/factor")
def get_index_factor(
    session: SessionDep,
    ts_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> Any:
    """获取指数技术因子数据"""
    items = IndexService.get_index_factor_list(
        session=session,
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"data": items}


# ==================== 同步接口 Payload 定义 ====================

class IndexBasicSyncPayload(BaseModel):
    keyword: Optional[str] = None
    market: Optional[str] = None


class IndexDailySyncPayload(BaseModel):
    ts_code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class IndexDailybasicSyncPayload(BaseModel):
    ts_code: Optional[str] = None
    trade_date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class IndexWeeklySyncPayload(BaseModel):
    ts_code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class IndexClassifySyncPayload(BaseModel):
    index_code: Optional[str] = None
    level: Optional[str] = None
    parent_code: Optional[str] = None
    src: str = "SW2021"


class IndexMemberSyncPayload(BaseModel):
    l1_code: Optional[str] = None
    l2_code: Optional[str] = None
    l3_code: Optional[str] = None
    ts_code: Optional[str] = None
    is_new: str = "Y"


class SwDailySyncPayload(BaseModel):
    ts_code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class IndexGlobalSyncPayload(BaseModel):
    ts_code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class IndexFactorSyncPayload(BaseModel):
    ts_code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ==================== 工具函数 ====================

def _to_yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)


def _get_last_date(session: Session, table: str, ts_code: str, date_col: str = "trade_date") -> Optional[date]:
    """获取指定表的最后日期"""
    sql = text(f"SELECT MAX({date_col}) AS last_date FROM {table} WHERE ts_code = :ts_code")
    with session.connection() as conn:
        row = conn.execute(sql, {"ts_code": ts_code}).fetchone()
        return row[0] if row and row[0] else None


def _upsert_records(session: Session, table: str, records: List[dict], primary_keys: List[str]) -> tuple[int, int]:
    """通用 upsert 函数"""
    if not records:
        return 0, 0
    
    first_keys = list(records[0].keys())
    keys = [k for k in first_keys if k not in ['id', 'update_time', 'create_time']]
    
    if not all(pk in keys for pk in primary_keys):
        logger.error(f"Upsert failed: Missing primary keys {primary_keys}")
        return 0, len(records)

    # 处理日期格式 (YYYYMMDD -> YYYY-MM-DD)
    processed_records = []
    for r in records:
        new_r = {k: r.get(k) for k in keys}
        # 处理 trade_date 或类似日期字段
        for date_key in ['trade_date', 'nav_date', 'in_date', 'out_date', 'base_date', 'list_date', 'exp_date']:
            if date_key in new_r:
                td = new_r.get(date_key)
                if isinstance(td, str) and len(td) == 8:
                    try:
                        new_r[date_key] = f"{td[:4]}-{td[4:6]}-{td[6:]}"
                    except:
                        pass
        processed_records.append(new_r)
    
    records = processed_records

    # 构建 INSERT SQL
    cols = ", ".join(keys)
    vals = ", ".join([f":{k}" for k in keys])
    
    # 构建 UPDATE SET (排除主键)
    update_set = ", ".join([f"{k} = EXCLUDED.{k}" for k in keys if k not in primary_keys])
    
    pk_constraint = ", ".join(primary_keys)
    
    sql_str = f"""
        INSERT INTO {table} ({cols})
        VALUES ({vals})
        ON CONFLICT ({pk_constraint})
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
            logger.error(f"Upsert batch failed: {e}\n{traceback.format_exc()}")
            session.rollback()
            # 降级为逐条插入
            for rec in batch:
                try:
                    session.execute(text(sql_str), rec)
                    session.commit()
                    success += 1
                except Exception as e2:
                    logger.error(f"Upsert single failed: {e2}")
                    session.rollback()
                    failed += 1
                    
    return success, failed


# ==================== 同步接口 ====================

@router.post("/basic/sync")
def sync_index_basic(session: SessionDep, payload: IndexBasicSyncPayload) -> Any:
    """同步指数基础信息"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync index_basic request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {}
        if payload.market:
            params["market"] = payload.market
        
        logger.info(f"Fetching index_basic with params: {params}")
        df = pro.index_basic(**params)
        
        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")
        
        # 数据清洗
        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")
        
        # 字段映射：desc -> desc_text
        for r in rows:
            if 'desc' in r:
                r['desc_text'] = r.pop('desc')
        
        succ, fail = _upsert_records(session, "index.index_basic", rows, ["ts_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}
        
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


@router.post("/daily/sync")
def sync_index_daily(session: SessionDep, payload: IndexDailySyncPayload) -> Any:
    """
    同步指数日线行情
    支持单个 ts_code 或多个 ts_code（逗号分隔，如：000001.SH,399001.SZ）
    """
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync index_daily request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.ts_code:
        raise HTTPException(status_code=400, detail="必须指定指数代码")

    # 解析多个 ts_code（支持逗号分隔）
    ts_codes = [c.strip() for c in payload.ts_code.split(',') if c.strip()]
    if not ts_codes:
        raise HTTPException(status_code=400, detail="必须指定至少一个指数代码")

    total_success = 0
    total_failed = 0

    # 循环处理每个 ts_code
    for ts_code in ts_codes:
        # 确定时间范围
        start_d = None
        if payload.start_date:
            start_d = _parse_iso_date(payload.start_date)
        else:
            last_date = _get_last_date(session, "index.index_daily", ts_code)
            if last_date:
                start_d = last_date + timedelta(days=1)
            else:
                start_d = date.today() - timedelta(days=365*3)
        
        end_d = date.today()
        if payload.end_date:
            end_d = _parse_iso_date(payload.end_date)
            
        if start_d > end_d:
            logger.info(f"No new data to sync for {ts_code}")
            continue

        # 按年循环获取
        curr = start_d
        while curr <= end_d:
            next_year = curr + timedelta(days=365)
            batch_end = min(next_year, end_d)
            
            params = {
                "ts_code": ts_code,
                "start_date": _to_yyyymmdd(curr),
                "end_date": _to_yyyymmdd(batch_end)
            }
            try:
                logger.info(f"Fetching index_daily for {ts_code}, range: {params['start_date']} - {params['end_date']}")
                df = pro.index_daily(**params)
                
                if df is not None and not df.empty:
                    df = df.where(pd.notnull(df), None)
                    rows = df.to_dict("records")
                    succ, fail = _upsert_records(session, "index.index_daily", rows, ["ts_code", "trade_date"])
                    total_success += succ
                    total_failed += fail
            except Exception as e:
                logger.error(f"Tushare API failed for {ts_code}: {e}\n{traceback.format_exc()}")
                total_failed += 1
            
            curr = batch_end + timedelta(days=1)

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


@router.post("/dailybasic/sync")
def sync_index_dailybasic(session: SessionDep, payload: IndexDailybasicSyncPayload) -> Any:
    """
    同步大盘指数每日指标
    支持单个 ts_code 或多个 ts_code（逗号分隔，如：000001.SH,399001.SZ）
    """
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync index_dailybasic request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    total_success = 0
    total_failed = 0

    # 按日期或日期范围同步
    if payload.trade_date:
        params = {"trade_date": payload.trade_date.replace("-", "")}
        try:
            logger.info(f"Fetching index_dailybasic for date: {payload.trade_date}")
            df = pro.index_dailybasic(**params)
            
            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "index.index_dailybasic", rows, ["ts_code", "trade_date"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
    elif payload.ts_code:
        # 解析多个 ts_code（支持逗号分隔）
        ts_codes = [c.strip() for c in payload.ts_code.split(',') if c.strip()]
        if not ts_codes:
            raise HTTPException(status_code=400, detail="必须指定至少一个指数代码")
        
        # 循环处理每个 ts_code
        for ts_code in ts_codes:
            start_d = None
            if payload.start_date:
                start_d = _parse_iso_date(payload.start_date)
            else:
                last_date = _get_last_date(session, "index.index_dailybasic", ts_code)
                if last_date:
                    start_d = last_date + timedelta(days=1)
                else:
                    start_d = date.today() - timedelta(days=365)
            
            end_d = date.today()
            if payload.end_date:
                end_d = _parse_iso_date(payload.end_date)
            
            if start_d > end_d:
                logger.info(f"No new data to sync for {ts_code}")
                continue
            
            params = {
                "ts_code": ts_code,
                "start_date": _to_yyyymmdd(start_d),
                "end_date": _to_yyyymmdd(end_d)
            }
            try:
                logger.info(f"Fetching index_dailybasic for {ts_code}, range: {params['start_date']} - {params['end_date']}")
                df = pro.index_dailybasic(**params)
                
                if df is not None and not df.empty:
                    df = df.where(pd.notnull(df), None)
                    rows = df.to_dict("records")
                    succ, fail = _upsert_records(session, "index.index_dailybasic", rows, ["ts_code", "trade_date"])
                    total_success += succ
                    total_failed += fail
            except Exception as e:
                logger.error(f"Tushare API failed for {ts_code}: {e}\n{traceback.format_exc()}")
                total_failed += 1
    else:
        raise HTTPException(status_code=400, detail="必须指定 trade_date 或 ts_code")

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


@router.post("/weekly/sync")
def sync_index_weekly(session: SessionDep, payload: IndexWeeklySyncPayload) -> Any:
    """
    同步指数周线行情
    支持单个 ts_code 或多个 ts_code（逗号分隔，如：000001.SH,399001.SZ）
    """
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync index_weekly request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.ts_code:
        raise HTTPException(status_code=400, detail="必须指定指数代码")

    # 解析多个 ts_code（支持逗号分隔）
    ts_codes = [c.strip() for c in payload.ts_code.split(',') if c.strip()]
    if not ts_codes:
        raise HTTPException(status_code=400, detail="必须指定至少一个指数代码")

    total_success = 0
    total_failed = 0

    # 循环处理每个 ts_code
    for ts_code in ts_codes:
        # 确定时间范围
        start_d = None
        if payload.start_date:
            start_d = _parse_iso_date(payload.start_date)
        else:
            last_date = _get_last_date(session, "index.index_weekly", ts_code)
            if last_date:
                start_d = last_date + timedelta(days=1)
            else:
                start_d = date.today() - timedelta(days=365*3)
        
        end_d = date.today()
        if payload.end_date:
            end_d = _parse_iso_date(payload.end_date)
            
        if start_d > end_d:
            logger.info(f"No new data to sync for {ts_code}")
            continue
        
        params = {
            "ts_code": ts_code,
            "start_date": _to_yyyymmdd(start_d),
            "end_date": _to_yyyymmdd(end_d)
        }
        try:
            logger.info(f"Fetching index_weekly for {ts_code}, range: {params['start_date']} - {params['end_date']}")
            df = pro.index_weekly(**params)
            
            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "index.index_weekly", rows, ["ts_code", "trade_date"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed for {ts_code}: {e}\n{traceback.format_exc()}")
            total_failed += 1

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


@router.post("/classify/sync")
def sync_index_classify(session: SessionDep, payload: IndexClassifySyncPayload) -> Any:
    """同步申万行业分类"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync index_classify request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    try:
        params = {"src": payload.src.lower()}  # Tushare API 使用小写
        if payload.index_code:
            params["index_code"] = payload.index_code
        if payload.level:
            params["level"] = payload.level
        if payload.parent_code is not None:
            params["parent_code"] = payload.parent_code
        
        logger.info(f"Fetching index_classify with params: {params}")
        df = pro.index_classify(**params)
        
        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")
        
        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")
        
        # 转换 src 为大写（SW2014/SW2021）
        for r in rows:
            if 'src' in r and r['src']:
                r['src'] = r['src'].upper()
        
        succ, fail = _upsert_records(session, "index.index_classify", rows, ["index_code"])
        return {"message": "sync triggered", "success": succ, "failed": fail}
        
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


@router.post("/member/sync")
def sync_index_member(session: SessionDep, payload: IndexMemberSyncPayload) -> Any:
    """同步申万行业成分构成"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync index_member_all request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not any([payload.l1_code, payload.l2_code, payload.l3_code, payload.ts_code]):
        raise HTTPException(status_code=400, detail="必须指定 l1_code/l2_code/l3_code/ts_code 之一")

    try:
        params = {"is_new": payload.is_new}
        if payload.l1_code:
            params["l1_code"] = payload.l1_code
        if payload.l2_code:
            params["l2_code"] = payload.l2_code
        if payload.l3_code:
            params["l3_code"] = payload.l3_code
        if payload.ts_code:
            params["ts_code"] = payload.ts_code
        
        logger.info(f"Fetching index_member_all with params: {params}")
        df = pro.index_member_all(**params)
        
        if df is None or df.empty:
            logger.warning("Tushare returned empty DataFrame")
            return {"message": "No data found", "success": 0, "failed": 0}

        logger.info(f"Tushare returned {len(df)} records")
        
        df = df.where(pd.notnull(df), None)
        rows = df.to_dict("records")
        
        succ, fail = _upsert_records(session, "index.index_member_all", rows, ["l3_code", "ts_code", "is_new"])
        return {"message": "sync triggered", "success": succ, "failed": fail}
        
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"同步失败: {e}")


@router.post("/sw/daily/sync")
def sync_sw_daily(session: SessionDep, payload: SwDailySyncPayload) -> Any:
    """同步申万行业日线行情"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync sw_daily request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    total_success = 0
    total_failed = 0

    # 按日期或日期范围同步
    if payload.ts_code:
        start_d = _parse_iso_date(payload.start_date) if payload.start_date else date.today() - timedelta(days=365)
        end_d = _parse_iso_date(payload.end_date) if payload.end_date else date.today()
        
        params = {
            "ts_code": payload.ts_code,
            "start_date": _to_yyyymmdd(start_d),
            "end_date": _to_yyyymmdd(end_d)
        }
        try:
            logger.info(f"Fetching sw_daily for {payload.ts_code}, range: {params['start_date']} - {params['end_date']}")
            df = pro.sw_daily(**params)
            
            if df is not None and not df.empty:
                df = df.where(pd.notnull(df), None)
                rows = df.to_dict("records")
                succ, fail = _upsert_records(session, "index.sw_daily", rows, ["ts_code", "trade_date"])
                total_success += succ
                total_failed += fail
        except Exception as e:
            logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
    else:
        # 按日期同步所有指数
        if not payload.start_date or not payload.end_date:
            raise HTTPException(status_code=400, detail="未指定 ts_code 时必须指定 start_date 和 end_date")
        
        start_d = _parse_iso_date(payload.start_date)
        end_d = _parse_iso_date(payload.end_date)
        
        curr = start_d
        while curr <= end_d:
            params = {"trade_date": _to_yyyymmdd(curr)}
            try:
                logger.info(f"Fetching sw_daily for date: {params['trade_date']}")
                df = pro.sw_daily(**params)
                
                if df is not None and not df.empty:
                    df = df.where(pd.notnull(df), None)
                    rows = df.to_dict("records")
                    succ, fail = _upsert_records(session, "index.sw_daily", rows, ["ts_code", "trade_date"])
                    total_success += succ
                    total_failed += fail
            except Exception as e:
                logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")
            
            curr += timedelta(days=1)

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


@router.post("/global/sync")
def sync_index_global(session: SessionDep, payload: IndexGlobalSyncPayload) -> Any:
    """同步国际指数"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync index_global request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.ts_code:
        raise HTTPException(status_code=400, detail="必须指定指数代码")

    total_success = 0
    total_failed = 0

    start_d = _parse_iso_date(payload.start_date) if payload.start_date else date.today() - timedelta(days=365)
    end_d = _parse_iso_date(payload.end_date) if payload.end_date else date.today()
    
    params = {
        "ts_code": payload.ts_code,
        "start_date": _to_yyyymmdd(start_d),
        "end_date": _to_yyyymmdd(end_d)
    }
    try:
        logger.info(f"Fetching index_global for {payload.ts_code}, range: {params['start_date']} - {params['end_date']}")
        df = pro.index_global(**params)
        
        if df is not None and not df.empty:
            df = df.where(pd.notnull(df), None)
            rows = df.to_dict("records")
            succ, fail = _upsert_records(session, "index.index_global", rows, ["ts_code", "trade_date"])
            total_success += succ
            total_failed += fail
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}


@router.post("/factor/sync")
def sync_index_factor(session: SessionDep, payload: IndexFactorSyncPayload) -> Any:
    """同步指数技术因子"""
    if not settings.TUSHARE_TOKEN:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")
    try:
        import tushare as ts
        import pandas as pd
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tushare 未安装或初始化失败: {e}")
    
    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    logger.info(f"Sync idx_factor_pro request received. Payload: {payload}")

    if settings.TUSHARE_API_URL:
        pro._DataApi__http_url = settings.TUSHARE_API_URL

    if not payload.ts_code:
        raise HTTPException(status_code=400, detail="必须指定指数代码")

    total_success = 0
    total_failed = 0

    start_d = _parse_iso_date(payload.start_date) if payload.start_date else date.today() - timedelta(days=365)
    end_d = _parse_iso_date(payload.end_date) if payload.end_date else date.today()
    
    params = {
        "ts_code": payload.ts_code,
        "start_date": _to_yyyymmdd(start_d),
        "end_date": _to_yyyymmdd(end_d)
    }
    try:
        logger.info(f"Fetching idx_factor_pro for {payload.ts_code}, range: {params['start_date']} - {params['end_date']}")
        df = pro.idx_factor_pro(**params)
        
        if df is not None and not df.empty:
            # 数据清洗
            numeric_cols = df.columns.drop(['ts_code', 'trade_date'])
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.where(pd.notnull(df), None)
            rows = df.to_dict("records")
            succ, fail = _upsert_records(session, "index.index_factor", rows, ["ts_code", "trade_date"])
            total_success += succ
            total_failed += fail
    except Exception as e:
        logger.error(f"Tushare API failed: {e}\n{traceback.format_exc()}")

    return {"message": "sync triggered", "success": total_success, "failed": total_failed}

