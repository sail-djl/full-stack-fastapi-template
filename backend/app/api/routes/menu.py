from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.crud import (
    create_permission,
    delete_permission,
    get_permission_by_id,
    get_permission_by_key,
    get_permission_tree,
    update_permission,
)
from app.models import Permission, PermissionCreate, PermissionPublic, PermissionUpdate, PermissionsPublic, Message


router = APIRouter(prefix="/permissions", tags=["permissions"])


def build_permission_tree(permissions: list[Permission]) -> list[PermissionPublic]:
    """将扁平权限列表构建为树形结构"""
    # 创建权限字典，初始化 children 为空列表
    permission_dict: dict[int, PermissionPublic] = {}
    for permission in permissions:
        permission_public = PermissionPublic.model_validate(permission)
        permission_public.children = []
        permission_dict[permission.id] = permission_public
    
    root_permissions = []
    
    # 构建树形结构
    for permission in permissions:
        permission_public = permission_dict[permission.id]
        if permission.parent_id is None:
            root_permissions.append(permission_public)
        else:
            parent = permission_dict.get(permission.parent_id)
            if parent and parent.children is not None:
                parent.children.append(permission_public)
    
    # 对每个权限的子权限进行排序
    def sort_children(permission: PermissionPublic):
        if permission.children:
            permission.children.sort(key=lambda x: (x.sort_order, x.id))
            for child in permission.children:
                sort_children(child)
        else:
            # 如果没有子权限，设置为 None（而不是空列表）
            permission.children = None
    
    for permission in root_permissions:
        sort_children(permission)
    
    root_permissions.sort(key=lambda x: (x.sort_order, x.id))
    return root_permissions


@router.get("/tree", response_model=list[PermissionPublic])
def get_permission_tree_api(session: SessionDep) -> Any:
    """
    获取权限树（只返回启用的权限，已构建为树形结构）
    """
    permissions = get_permission_tree(session=session)
    permission_tree = build_permission_tree(permissions)
    return permission_tree


@router.get("/", response_model=PermissionsPublic)
def read_permissions(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> Any:
    """
    获取所有权限（扁平列表，用于管理界面）
    """
    count_statement = select(func.count()).select_from(Permission)
    count = session.exec(count_statement).one()
    statement = select(Permission).offset(skip).limit(limit).order_by(Permission.sort_order, Permission.id)
    permissions = session.exec(statement).all()
    return PermissionsPublic(data=[PermissionPublic.model_validate(p) for p in permissions], count=count)


@router.get("/{id}", response_model=PermissionPublic)
def read_permission(session: SessionDep, id: int) -> Any:
    """
    根据ID获取权限
    """
    permission = get_permission_by_id(session=session, permission_id=id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    return PermissionPublic.model_validate(permission)


@router.post("/", response_model=PermissionPublic)
def create_permission_api(
    *, session: SessionDep, permission_in: PermissionCreate
) -> Any:
    """
    创建新权限
    """
    # 检查 key 是否已存在
    existing_permission = get_permission_by_key(session=session, key=permission_in.key)
    if existing_permission:
        raise HTTPException(status_code=400, detail="Permission with this key already exists")
    
    permission = create_permission(session=session, permission_in=permission_in)
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
    permission = get_permission_by_id(session=session, permission_id=id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    # 如果更新 key，检查新 key 是否已存在
    if permission_in.key and permission_in.key != permission.key:
        existing_permission = get_permission_by_key(session=session, key=permission_in.key)
        if existing_permission:
            raise HTTPException(status_code=400, detail="Permission with this key already exists")
    
    permission = update_permission(session=session, db_permission=permission, permission_in=permission_in)
    return PermissionPublic.model_validate(permission)


@router.delete("/{id}")
def delete_permission_api(
    session: SessionDep, id: int
) -> Message:
    """
    删除权限
    """
    permission = get_permission_by_id(session=session, permission_id=id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    delete_permission(session=session, permission_id=id)
    return Message(message="Permission deleted successfully")

