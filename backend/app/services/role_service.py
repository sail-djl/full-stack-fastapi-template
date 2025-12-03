"""角色相关业务逻辑服务"""
import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app import crud
from app.models import Role, RoleCreate, RolePermission, RoleUpdate


class RoleService:
    """角色业务逻辑服务"""

    @staticmethod
    def create_role(session: Session, role_in: RoleCreate) -> Role:
        """
        创建角色（包含业务逻辑：code 唯一性验证）
        """
        # 业务逻辑：检查 code 是否已存在
        existing_role = crud.get_role_by_code(session=session, code=role_in.code)
        if existing_role:
            raise HTTPException(status_code=400, detail="Role with this code already exists")

        return crud.create_role(session=session, role_in=role_in)

    @staticmethod
    def update_role(
        session: Session, role_id: uuid.UUID, role_in: RoleUpdate
    ) -> Role:
        """
        更新角色（包含业务逻辑：code 唯一性验证）
        """
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # 业务逻辑：如果更新 code，检查新 code 是否已存在
        if role_in.code and role_in.code != role.code:
            existing_role = crud.get_role_by_code(session=session, code=role_in.code)
            if existing_role:
                raise HTTPException(status_code=400, detail="Role with this code already exists")

        return crud.update_role(session=session, db_role=role, role_in=role_in)

    @staticmethod
    def delete_role(session: Session, role_id: uuid.UUID) -> None:
        """
        删除角色（包含业务逻辑：存在性验证）
        """
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        crud.delete_role(session=session, role_id=role_id)

    @staticmethod
    def get_roles(session: Session, skip: int = 0, limit: int = 100) -> tuple[list[Role], int]:
        """
        获取角色列表（包含业务逻辑：分页、计数）
        """
        count_statement = select(func.count()).select_from(Role)
        count = session.exec(count_statement).one()

        roles = crud.get_roles(session=session, skip=skip, limit=limit)
        return list(roles), count

    @staticmethod
    def get_role_by_id(session: Session, role_id: uuid.UUID) -> Role:
        """
        根据ID获取角色（包含业务逻辑：存在性验证）
        """
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role

    @staticmethod
    def assign_permissions_to_role(
        session: Session, role_id: uuid.UUID, permission_ids: list[int]
    ) -> None:
        """
        为角色分配权限（包含业务逻辑：验证角色和权限存在）
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
        为角色添加单个权限（包含业务逻辑：验证存在性、防止重复）
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
        从角色移除权限（包含业务逻辑：验证角色存在）
        """
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        crud.remove_permission_from_role(session=session, role_id=role_id, permission_id=permission_id)

    @staticmethod
    def get_role_permissions(session: Session, role_id: uuid.UUID) -> list:
        """
        获取角色的所有权限（包含业务逻辑：验证角色存在）
        """
        from app.models import Permission

        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        return crud.get_role_permissions(session=session, role_id=role_id)

