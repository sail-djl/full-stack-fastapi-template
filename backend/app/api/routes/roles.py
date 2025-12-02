import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import (
    Message,
    Permission,
    PermissionPublic,
    Role,
    RoleCreate,
    RolePermission,
    RolePublic,
    RolesPublic,
    RoleUpdate,
    UserRole,
)

router = APIRouter(prefix="/roles", tags=["roles"])


# ============================================
# Role (角色) 路由
# ============================================
@router.get("/", response_model=RolesPublic)
def read_roles(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    获取所有角色
    """
    count_statement = select(func.count()).select_from(Role)
    count = session.exec(count_statement).one()
    
    roles = crud.get_roles(session=session, skip=skip, limit=limit)
    
    return RolesPublic(data=[RolePublic.model_validate(role) for role in roles], count=count)


@router.get("/{role_id}", response_model=RolePublic)
def read_role(role_id: uuid.UUID, session: SessionDep) -> Any:
    """
    根据ID获取角色
    """
    role = crud.get_role_by_id(session=session, role_id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return RolePublic.model_validate(role)


@router.post("/", dependencies=[Depends(get_current_active_superuser)], response_model=RolePublic)
def create_role_api(*, session: SessionDep, role_in: RoleCreate) -> Any:
    """
    创建新角色
    """
    # 检查 code 是否已存在
    existing_role = crud.get_role_by_code(session=session, code=role_in.code)
    if existing_role:
        raise HTTPException(status_code=400, detail="Role with this code already exists")
    
    role = crud.create_role(session=session, role_in=role_in)
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
    role = crud.get_role_by_id(session=session, role_id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # 如果更新 code，检查新 code 是否已存在
    if role_in.code and role_in.code != role.code:
        existing_role = crud.get_role_by_code(session=session, code=role_in.code)
        if existing_role:
            raise HTTPException(status_code=400, detail="Role with this code already exists")
    
    role = crud.update_role(session=session, db_role=role, role_in=role_in)
    return RolePublic.model_validate(role)


@router.delete("/{role_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_role_api(session: SessionDep, role_id: uuid.UUID) -> Message:
    """
    删除角色
    """
    role = crud.get_role_by_id(session=session, role_id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    crud.delete_role(session=session, role_id=role_id)
    return Message(message="Role deleted successfully")


# ============================================
# Role-Permission (角色权限关联) 路由
# ============================================
@router.get("/{role_id}/permissions", response_model=list[PermissionPublic])
def get_role_permissions(role_id: uuid.UUID, session: SessionDep) -> Any:
    """
    获取角色的所有权限
    """
    role = crud.get_role_by_id(session=session, role_id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    permissions = crud.get_role_permissions(session=session, role_id=role_id)
    return [PermissionPublic.model_validate(p) for p in permissions]


@router.post(
    "/{role_id}/permissions",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def assign_permissions_to_role(
    role_id: uuid.UUID,
    permission_ids: list[int],  # 改为 int 类型
    session: SessionDep,
) -> Any:
    """
    为角色分配权限（替换所有现有权限）
    """
    role = crud.get_role_by_id(session=session, role_id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # 验证所有权限是否存在
    for permission_id in permission_ids:
        permission = crud.get_permission_by_id(session=session, permission_id=permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail=f"Permission {permission_id} not found")
    
    crud.set_role_permissions(session=session, role_id=role_id, permission_ids=permission_ids)
    return Message(message="Permissions assigned successfully")


@router.post(
    "/{role_id}/permissions/{permission_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def assign_permission_to_role(
    role_id: uuid.UUID,
    permission_id: int,  # 改为 int 类型
    session: SessionDep,
) -> Any:
    """
    为角色添加单个权限
    """
    role = crud.get_role_by_id(session=session, role_id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    permission = crud.get_permission_by_id(session=session, permission_id=permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    # 检查是否已存在
    statement = select(RolePermission).where(
        RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
    )
    existing = session.exec(statement).first()
    if existing:
        raise HTTPException(status_code=400, detail="Permission already assigned to role")
    
    crud.assign_permission_to_role(session=session, role_id=role_id, permission_id=permission_id)
    return Message(message="Permission assigned successfully")


@router.delete(
    "/{role_id}/permissions/{permission_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def remove_permission_from_role(
    role_id: uuid.UUID,
    permission_id: int,  # 改为 int 类型
    session: SessionDep,
) -> Any:
    """
    从角色移除权限
    """
    role = crud.get_role_by_id(session=session, role_id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    crud.remove_permission_from_role(session=session, role_id=role_id, permission_id=permission_id)
    return Message(message="Permission removed successfully")

