import uuid
from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    Message,
    PermissionPublic,
    RoleCreate,
    RolePublic,
    RolesPublic,
    RoleUpdate,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


# ============================================
# Role (角色) 路由
# ============================================
@router.get("/", response_model=RolesPublic)
def read_roles(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有角色
    """
    roles, count = RoleService.get_roles(session=session, skip=skip, limit=limit)
    return RolesPublic(data=[RolePublic.model_validate(role) for role in roles], count=count)


@router.get("/{role_id}", response_model=RolePublic)
def read_role(role_id: uuid.UUID, session: SessionDep) -> Any:
    """
    根据ID获取角色
    """
    role = RoleService.get_role_by_id(session=session, role_id=role_id)
    return RolePublic.model_validate(role)


@router.post("/", dependencies=[Depends(get_current_active_superuser)], response_model=RolePublic)
def create_role_api(*, session: SessionDep, role_in: RoleCreate) -> Any:
    """
    创建新角色
    """
    role = RoleService.create_role(session=session, role_in=role_in)
    return RolePublic.model_validate(role)


@router.patch(
    "/{role_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=RolePublic,
)
def update_role_api(
    *,
    session: SessionDep,
    role_id: uuid.UUID,
    role_in: RoleUpdate,
) -> Any:
    """
    更新角色
    """
    role = RoleService.update_role(session=session, role_id=role_id, role_in=role_in)
    return RolePublic.model_validate(role)


@router.delete("/{role_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_role_api(session: SessionDep, role_id: uuid.UUID) -> Message:
    """
    删除角色
    """
    RoleService.delete_role(session=session, role_id=role_id)
    return Message(message="Role deleted successfully")


# ============================================
# Role-Permission (角色权限关联) 路由
# ============================================
@router.get("/{role_id}/permissions", response_model=list[PermissionPublic])
def get_role_permissions(role_id: uuid.UUID, session: SessionDep) -> Any:
    """
    获取角色的所有权限
    """
    permissions = RoleService.get_role_permissions(session=session, role_id=role_id)
    return [PermissionPublic.model_validate(p) for p in permissions]


@router.post(
    "/{role_id}/permissions",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def assign_permissions_to_role(
    role_id: uuid.UUID,
    permission_ids: list[int],
    session: SessionDep,
) -> Any:
    """
    为角色分配权限（替换所有现有权限）
    """
    RoleService.assign_permissions_to_role(
        session=session, role_id=role_id, permission_ids=permission_ids
    )
    return Message(message="Permissions assigned successfully")


@router.post(
    "/{role_id}/permissions/{permission_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def assign_permission_to_role(
    role_id: uuid.UUID,
    permission_id: int,
    session: SessionDep,
) -> Any:
    """
    为角色添加单个权限
    """
    RoleService.assign_permission_to_role(
        session=session, role_id=role_id, permission_id=permission_id
    )
    return Message(message="Permission assigned successfully")


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def remove_permission_from_role(
    role_id: uuid.UUID,
    permission_id: int,
    session: SessionDep,
) -> Any:
    """
    从角色移除权限
    """
    RoleService.remove_permission_from_role(
        session=session, role_id=role_id, permission_id=permission_id
    )
    return Message(message="Permission removed successfully")
