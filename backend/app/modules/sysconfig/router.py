"""系统配置API路由"""
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.api.deps import SessionDep, CurrentUser
from app.modules.sysconfig.service import SystemConfigService

router = APIRouter(prefix="/system-config", tags=["system-config"])


# ==================== 请求/响应模型 ====================

class SystemConfigBase(BaseModel):
    """系统配置基础模型"""
    config_category: str
    config_type: str
    config_key: str = "default"
    config_value: dict[str, Any]
    is_active: bool = True
    is_default: bool = False
    description: Optional[str] = None
    version: int = 1


class SystemConfigCreate(BaseModel):
    """创建系统配置请求模型"""
    config_category: str
    config_type: str
    config_key: Optional[str] = "default"
    config_value: dict[str, Any]
    is_active: Optional[bool] = True
    is_default: Optional[bool] = False
    description: Optional[str] = None
    version: Optional[int] = 1
    created_by: Optional[str] = None


class SystemConfigUpdate(BaseModel):
    """更新系统配置请求模型"""
    config_category: Optional[str] = None
    config_type: Optional[str] = None
    config_key: Optional[str] = None
    config_value: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    description: Optional[str] = None
    version: Optional[int] = None
    updated_by: Optional[str] = None


class SystemConfigPublic(BaseModel):
    """系统配置响应模型"""
    id: int
    config_category: str
    config_type: str
    config_key: str
    config_value: dict[str, Any]
    is_active: bool
    is_default: bool
    description: Optional[str] = None
    version: int
    created_at: str
    updated_at: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True


class SystemConfigListResponse(BaseModel):
    """系统配置列表响应模型"""
    data: list[SystemConfigPublic]
    count: int


# ==================== API接口 ====================

@router.get("/", response_model=SystemConfigListResponse)
def get_system_config_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    config_category: Optional[str] = None,
    config_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_default: Optional[bool] = None,
) -> Any:
    """
    获取系统配置列表
    """
    items, total = SystemConfigService.get_system_config_list(
        session=session,
        skip=skip,
        limit=limit,
        config_category=config_category,
        config_type=config_type,
        is_active=is_active,
        is_default=is_default,
    )
    return SystemConfigListResponse(
        data=[SystemConfigPublic(**item) for item in items],
        count=total,
    )


@router.get("/{config_id}", response_model=SystemConfigPublic)
def get_system_config_by_id(
    config_id: int,
    session: SessionDep,
) -> Any:
    """
    根据ID获取系统配置
    """
    config = SystemConfigService.get_system_config_by_id(session=session, config_id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return SystemConfigPublic(**config)


@router.post("/", response_model=SystemConfigPublic)
def create_system_config(
    *,
    session: SessionDep,
    config_in: SystemConfigCreate,
    current_user: CurrentUser = None,
) -> Any:
    """
    创建系统配置
    """
    created_by = str(current_user.id) if current_user else config_in.created_by

    config = SystemConfigService.create_system_config(
        session=session,
        config_category=config_in.config_category,
        config_type=config_in.config_type,
        config_key=config_in.config_key or "default",
        config_value=config_in.config_value,
        is_active=config_in.is_active if config_in.is_active is not None else True,
        is_default=config_in.is_default if config_in.is_default is not None else False,
        description=config_in.description,
        version=config_in.version if config_in.version is not None else 1,
        created_by=created_by,
    )
    return SystemConfigPublic(**config)


@router.patch("/{config_id}", response_model=SystemConfigPublic)
def update_system_config(
    *,
    session: SessionDep,
    config_id: int,
    config_in: SystemConfigUpdate,
    current_user: CurrentUser = None,
) -> Any:
    """
    更新系统配置
    """
    # 检查配置是否存在
    existing = SystemConfigService.get_system_config_by_id(session=session, config_id=config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置不存在")

    updated_by = str(current_user.id) if current_user else config_in.updated_by

    config = SystemConfigService.update_system_config(
        session=session,
        config_id=config_id,
        config_category=config_in.config_category,
        config_type=config_in.config_type,
        config_key=config_in.config_key,
        config_value=config_in.config_value,
        is_active=config_in.is_active,
        is_default=config_in.is_default,
        description=config_in.description,
        version=config_in.version,
        updated_by=updated_by,
    )
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return SystemConfigPublic(**config)


@router.delete("/{config_id}")
def delete_system_config(
    *,
    session: SessionDep,
    config_id: int,
) -> Any:
    """
    删除系统配置
    """
    # 检查配置是否存在
    existing = SystemConfigService.get_system_config_by_id(session=session, config_id=config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置不存在")

    success = SystemConfigService.delete_system_config(session=session, config_id=config_id)
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {"message": "配置已删除"}


@router.get("/default/{config_category}/{config_type}", response_model=SystemConfigPublic)
def get_default_config(
    config_category: str,
    config_type: str,
    session: SessionDep,
) -> Any:
    """
    获取默认配置
    """
    config = SystemConfigService.get_default_config(
        session=session,
        config_category=config_category,
        config_type=config_type,
    )
    if not config:
        raise HTTPException(status_code=404, detail="未找到默认配置")
    return SystemConfigPublic(**config)

