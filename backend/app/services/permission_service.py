"""权限相关业务逻辑服务"""
import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app import crud
from app.models import Permission, PermissionCreate, PermissionPublic, PermissionUpdate, RolePermission


class PermissionService:
    """权限业务逻辑服务"""

    @staticmethod
    def create_permission(session: Session, permission_in: PermissionCreate) -> Permission:
        """
        创建权限（包含业务逻辑：key 唯一性验证、父节点有效性）
        """
        existing_permission = crud.get_permission_by_key(session=session, key=permission_in.key)
        if existing_permission:
            raise HTTPException(status_code=400, detail="Permission with this key already exists")

        if permission_in.parent_id is not None:
            parent = crud.get_permission_by_id(session=session, permission_id=permission_in.parent_id)
            if parent is None:
                raise HTTPException(status_code=400, detail="Parent permission not found")

        return crud.create_permission(session=session, permission_in=permission_in)

    @staticmethod
    def update_permission(
        session: Session, permission_id: int, permission_in: PermissionUpdate
    ) -> Permission:
        """
        更新权限（包含业务逻辑：key 唯一性验证）
        """
        permission = crud.get_permission_by_id(session=session, permission_id=permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        # 业务逻辑：如果更新 key，检查新 key 是否已存在
        if permission_in.key and permission_in.key != permission.key:
            existing_permission = crud.get_permission_by_key(session=session, key=permission_in.key)
            if existing_permission:
                raise HTTPException(status_code=400, detail="Permission with this key already exists")

        return crud.update_permission(
            session=session, db_permission=permission, permission_in=permission_in
        )

    @staticmethod
    def delete_permission(session: Session, permission_id: int) -> None:
        """
        删除权限（包含业务逻辑：存在性验证）
        """
        permission = crud.get_permission_by_id(session=session, permission_id=permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        crud.delete_permission(session=session, permission_id=permission_id)

    @staticmethod
    def get_permissions(
        session: Session, skip: int = 0, limit: int = 100
    ) -> tuple[list[Permission], int]:
        """
        获取权限列表（包含业务逻辑：分页、计数）
        """
        count_statement = select(func.count()).select_from(Permission)
        count = session.exec(count_statement).one()

        statement = select(Permission).offset(skip).limit(limit).order_by(Permission.sort_order, Permission.id)
        permissions = session.exec(statement).all()
        return list(permissions), count

    @staticmethod
    def get_permission_by_id(session: Session, permission_id: int) -> Permission:
        """
        根据ID获取权限（包含业务逻辑：存在性验证）
        """
        permission = crud.get_permission_by_id(session=session, permission_id=permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        return permission

    @staticmethod
    def get_permission_tree(session: Session) -> list[Permission]:
        """
        获取权限树（扁平列表）
        """
        return crud.get_permission_tree(session=session)

    @staticmethod
    def build_permission_tree(permissions: list[Permission]) -> list[PermissionPublic]:
        """
        构建权限树（包含业务逻辑：树形结构构建）
        """
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

    @staticmethod
    def assign_permissions_to_role(
        session: Session, role_id: uuid.UUID, permission_ids: list[int]
    ) -> None:
        """
        为角色分配权限（批量，替换所有现有权限）
        包含业务逻辑：验证角色和权限存在
        """
        # 业务逻辑：验证角色存在
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # 业务逻辑：验证所有权限是否存在
        for permission_id in permission_ids:
            permission = crud.get_permission_by_id(session=session, permission_id=permission_id)
            if not permission:
                raise HTTPException(status_code=404, detail=f"Permission {permission_id} not found")

        crud.set_role_permissions(session=session, role_id=role_id, permission_ids=permission_ids)

    @staticmethod
    def assign_permission_to_role(
        session: Session, role_id: uuid.UUID, permission_id: int
    ) -> None:
        """
        为角色添加单个权限
        包含业务逻辑：验证存在性、防止重复
        """
        # 业务逻辑：验证角色存在
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # 业务逻辑：验证权限存在
        permission = crud.get_permission_by_id(session=session, permission_id=permission_id)
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        # 业务逻辑：检查是否已存在
        statement = select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
        )
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(status_code=400, detail="Permission already assigned to role")

        crud.assign_permission_to_role(session=session, role_id=role_id, permission_id=permission_id)

    @staticmethod
    def remove_permission_from_role(
        session: Session, role_id: uuid.UUID, permission_id: int
    ) -> None:
        """
        从角色移除权限
        包含业务逻辑：验证角色存在
        """
        # 业务逻辑：验证角色存在
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        crud.remove_permission_from_role(session=session, role_id=role_id, permission_id=permission_id)

    @staticmethod
    def get_role_permissions(session: Session, role_id: uuid.UUID) -> list[Permission]:
        """
        获取角色的所有权限
        包含业务逻辑：验证角色存在
        """
        # 业务逻辑：验证角色存在
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        return crud.get_role_permissions(session=session, role_id=role_id)

