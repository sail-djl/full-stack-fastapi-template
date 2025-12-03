from typing import Any

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.models import (
    Message,
    PermissionCreate,
    PermissionPublic,
    PermissionsPublic,
    PermissionUpdate,
)
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/tree", response_model=list[PermissionPublic])
def get_permission_tree_api(session: SessionDep) -> Any:
    """
    获取权限树（只返回启用的权限，已构建为树形结构）
    """
    permissions = PermissionService.get_permission_tree(session=session)
    permission_tree = PermissionService.build_permission_tree(permissions)
    return permission_tree


@router.get("/", response_model=PermissionsPublic)
def read_permissions(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> Any:
    """
    获取所有权限（扁平列表，用于管理界面）
    """
    permissions, count = PermissionService.get_permissions(session=session, skip=skip, limit=limit)
    return PermissionsPublic(data=[PermissionPublic.model_validate(p) for p in permissions], count=count)


@router.get("/{id}", response_model=PermissionPublic)
def read_permission(session: SessionDep, id: int) -> Any:
    """
    根据ID获取权限
    """
    permission = PermissionService.get_permission_by_id(session=session, permission_id=id)
    return PermissionPublic.model_validate(permission)


@router.post("/", response_model=PermissionPublic)
def create_permission_api(
    *, session: SessionDep, permission_in: PermissionCreate
) -> Any:
    """
    创建新权限
    """
    permission = PermissionService.create_permission(session=session, permission_in=permission_in)
    return PermissionPublic.model_validate(permission)


@router.put("/{id}", response_model=PermissionPublic)
def update_permission_api(
    *,
    session: SessionDep,
    id: int,
    permission_in: PermissionUpdate,
) -> Any:
    """
    更新权限
    """
    permission = PermissionService.update_permission(
        session=session, permission_id=id, permission_in=permission_in
    )
    return PermissionPublic.model_validate(permission)


@router.delete("/{id}")
def delete_permission_api(
    session: SessionDep, id: int
) -> Message:
    """
    删除权限
    """
    PermissionService.delete_permission(session=session, permission_id=id)
    return Message(message="Permission deleted successfully")
