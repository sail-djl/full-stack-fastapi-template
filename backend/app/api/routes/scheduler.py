from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_active_superuser
from app.models.user import User
from app.scheduler import scheduler

router = APIRouter(tags=["scheduler"])


@router.get("/jobs")
async def get_jobs(current_user: User = Depends(get_current_active_superuser)):
    """
    获取所有定时任务列表（仅超级用户）
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "func": f"{job.func_ref}" if hasattr(job, 'func_ref') else str(job.func),
        })
    return {"jobs": jobs, "total": len(jobs)}


@router.post("/jobs/{job_id}/pause")
async def pause_job(
    job_id: str,
    current_user: User = Depends(get_current_active_superuser),
):
    """
    暂停指定任务（仅超级用户）
    """
    try:
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

        scheduler.pause_job(job_id)
        return {"message": f"任务 {job_id} 已暂停", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/{job_id}/resume")
async def resume_job(
    job_id: str,
    current_user: User = Depends(get_current_active_superuser),
):
    """
    恢复指定任务（仅超级用户）
    """
    try:
        job = scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

        scheduler.resume_job(job_id)
        return {"message": f"任务 {job_id} 已恢复", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_superuser),
):
    """
    获取指定任务的详细信息（仅超级用户）
    """
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

    return {
        "id": job.id,
        "name": job.name,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": str(job.trigger),
        "func": f"{job.func_ref}" if hasattr(job, 'func_ref') else str(job.func),
    }




