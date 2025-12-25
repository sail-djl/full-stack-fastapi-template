"""用户配置API路由"""
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.api.deps import SessionDep, CurrentUser
from app.services.user_config_service import UserConfigService

router = APIRouter(prefix="/user-config", tags=["user-config"])


# ==================== 请求/响应模型 ====================

class UserConfigBase(BaseModel):
    """用户配置基础模型"""
    module: Optional[str] = None
    config_type: str
    config_key: str = "default"
    config_value: dict[str, Any]
    is_active: bool = True
    is_default: bool = False
    description: Optional[str] = None
    version: int = 1


class UserConfigCreate(UserConfigBase):
    """创建用户配置请求模型"""
    pass


class UserConfigUpdate(BaseModel):
    """更新用户配置请求模型"""
    module: Optional[str] = None
    config_type: Optional[str] = None
    config_key: Optional[str] = None
    config_value: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    description: Optional[str] = None
    version: Optional[int] = None


class UserConfigPublic(UserConfigBase):
    """用户配置响应模型"""
    id: int
    user_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserConfigListResponse(BaseModel):
    """用户配置列表响应模型"""
    data: list[UserConfigPublic]
    count: int


# ==================== API接口 ====================

@router.get("/", response_model=UserConfigListResponse)
def get_user_config_list(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    module: Optional[str] = None,
    config_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: CurrentUser = None,
) -> Any:
    """
    获取用户配置列表
    如果未指定user_id，则查询当前用户的配置
    """
    # 如果未指定user_id，使用当前登录用户的ID
    if user_id is None and current_user:
        user_id = str(current_user.id)

    items, total = UserConfigService.get_user_config_list(
        session=session,
        skip=skip,
        limit=limit,
        user_id=user_id,
        module=module,
        config_type=config_type,
        is_active=is_active,
    )
    return UserConfigListResponse(
        data=[UserConfigPublic(**item) for item in items],
        count=total,
    )


@router.get("/{config_id}", response_model=UserConfigPublic)
def get_user_config_by_id(
    config_id: int,
    session: SessionDep,
) -> Any:
    """
    根据ID获取用户配置
    """
    config = UserConfigService.get_user_config_by_id(session=session, config_id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return UserConfigPublic(**config)


@router.post("/", response_model=UserConfigPublic)
def create_user_config(
    *,
    session: SessionDep,
    config_in: UserConfigCreate,
    current_user: CurrentUser = None,
) -> Any:
    """
    创建用户配置
    如果未指定user_id，则创建为当前用户的配置
    """
    user_id = str(current_user.id) if current_user else None

    config = UserConfigService.create_user_config(
        session=session,
        user_id=user_id,
        module=config_in.module,
        config_type=config_in.config_type,
        config_key=config_in.config_key,
        config_value=config_in.config_value,
        is_active=config_in.is_active,
        is_default=config_in.is_default,
        description=config_in.description,
        version=config_in.version,
    )
    return UserConfigPublic(**config)


@router.patch("/{config_id}", response_model=UserConfigPublic)
def update_user_config(
    *,
    session: SessionDep,
    config_id: int,
    config_in: UserConfigUpdate,
    current_user: CurrentUser = None,
) -> Any:
    """
    更新用户配置
    """
    # 检查配置是否存在
    existing = UserConfigService.get_user_config_by_id(session=session, config_id=config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 检查权限：只能更新自己的配置或全局配置
    if existing.get("user_id") and current_user:
        if str(existing["user_id"]) != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权修改此配置")

    user_id = str(current_user.id) if current_user else existing.get("user_id")

    config = UserConfigService.update_user_config(
        session=session,
        config_id=config_id,
        user_id=user_id if config_in.module or config_in.config_type else None,
        module=config_in.module,
        config_type=config_in.config_type,
        config_key=config_in.config_key,
        config_value=config_in.config_value,
        is_active=config_in.is_active,
        is_default=config_in.is_default,
        description=config_in.description,
        version=config_in.version,
    )
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return UserConfigPublic(**config)


@router.delete("/{config_id}")
def delete_user_config(
    *,
    session: SessionDep,
    config_id: int,
    current_user: CurrentUser = None,
) -> Any:
    """
    删除用户配置
    """
    # 检查配置是否存在
    existing = UserConfigService.get_user_config_by_id(session=session, config_id=config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 检查权限：只能删除自己的配置或全局配置
    if existing.get("user_id") and current_user:
        if str(existing["user_id"]) != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权删除此配置")

    success = UserConfigService.delete_user_config(session=session, config_id=config_id)
    if not success:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {"message": "配置已删除"}


@router.get("/default/{config_type}", response_model=UserConfigPublic)
def get_default_config(
    config_type: str,
    session: SessionDep,
    current_user: CurrentUser = None,
) -> Any:
    """
    获取默认配置（优先用户配置，如果没有则返回全局默认配置）
    """
    user_id = str(current_user.id) if current_user else None
    config = UserConfigService.get_default_config(
        session=session,
        user_id=user_id,
        config_type=config_type,
    )
    if not config:
        raise HTTPException(status_code=404, detail="未找到默认配置")
    return UserConfigPublic(**config)





