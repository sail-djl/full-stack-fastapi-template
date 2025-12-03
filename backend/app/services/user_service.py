"""用户相关业务逻辑服务"""
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, col, delete, func, select

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    Message,
    Role,
    UpdatePassword,
    User,
    UserCreate,
    UserRegister,
    UserRole,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email


class UserService:
    """用户业务逻辑服务"""

    @staticmethod
    def create_user(session: Session, user_in: UserCreate) -> User:
        """
        创建用户（包含业务逻辑：邮箱验证、发送欢迎邮件）
        """
        # 业务逻辑：检查邮箱是否已存在
        user = crud.get_user_by_email(session=session, email=user_in.email)
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system.",
            )

        # 数据访问
        user = crud.create_user(session=session, user_create=user_in)

        # 业务逻辑：发送欢迎邮件
        if settings.emails_enabled and user_in.email:
            email_data = generate_new_account_email(
                email_to=user_in.email, username=user_in.email, password=user_in.password
            )
            send_email(
                email_to=user_in.email,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )

        return user

    @staticmethod
    def register_user(session: Session, user_in: UserRegister) -> User:
        """
        用户注册（包含业务逻辑：邮箱验证）
        """
        # 业务逻辑：检查邮箱是否已存在
        user = crud.get_user_by_email(session=session, email=user_in.email)
        if user:
            raise HTTPException(
                status_code=400,
                detail="The user with this email already exists in the system",
            )

        # 转换为 UserCreate
        user_create = UserCreate.model_validate(user_in)
        return crud.create_user(session=session, user_create=user_create)

    @staticmethod
    def update_user(
        session: Session, user_id: uuid.UUID, user_in: UserUpdate, current_user: User
    ) -> User:
        """
        更新用户（包含业务逻辑：权限检查、邮箱冲突检查）
        """
        db_user = session.get(User, user_id)
        if not db_user:
            raise HTTPException(
                status_code=404,
                detail="The user with this id does not exist in the system",
            )

        # 业务逻辑：如果更新邮箱，检查冲突
        if user_in.email:
            existing_user = crud.get_user_by_email(session=session, email=user_in.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=409, detail="User with this email already exists"
                )

        return crud.update_user(session=session, db_user=db_user, user_in=user_in)

    @staticmethod
    def update_user_me(session: Session, user_in: UserUpdateMe, current_user: User) -> User:
        """
        更新当前用户（包含业务逻辑：邮箱冲突检查）
        """
        # 业务逻辑：检查邮箱冲突
        if user_in.email:
            existing_user = crud.get_user_by_email(session=session, email=user_in.email)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=409, detail="User with this email already exists"
                )

        # 更新用户信息
        user_data = user_in.model_dump(exclude_unset=True)
        current_user.sqlmodel_update(user_data)
        session.add(current_user)
        session.commit()
        session.refresh(current_user)
        return current_user

    @staticmethod
    def update_password_me(session: Session, body: UpdatePassword, current_user: User) -> Message:
        """
        更新当前用户密码（包含业务逻辑：密码验证）
        """
        # 业务逻辑：验证当前密码
        if not verify_password(body.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")

        # 业务逻辑：检查新旧密码是否相同
        if body.current_password == body.new_password:
            raise HTTPException(
                status_code=400, detail="New password cannot be the same as the current one"
            )

        # 更新密码
        hashed_password = get_password_hash(body.new_password)
        current_user.hashed_password = hashed_password
        session.add(current_user)
        session.commit()
        return Message(message="Password updated successfully")

    @staticmethod
    def delete_user(session: Session, user_id: uuid.UUID, current_user: User) -> Message:
        """
        删除用户（包含业务逻辑：权限检查、防止删除自己）
        """
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 业务逻辑：防止超级用户删除自己
        if user == current_user:
            raise HTTPException(
                status_code=403, detail="Super users are not allowed to delete themselves"
            )

        # 业务逻辑：删除用户的所有 Item
        statement = delete(Item).where(col(Item.owner_id) == user_id)
        session.exec(statement)  # type: ignore

        # 删除用户
        session.delete(user)
        session.commit()
        return Message(message="User deleted successfully")

    @staticmethod
    def delete_user_me(session: Session, current_user: User) -> Message:
        """
        删除当前用户（包含业务逻辑：防止超级用户删除自己）
        """
        # 业务逻辑：防止超级用户删除自己
        if current_user.is_superuser:
            raise HTTPException(
                status_code=403, detail="Super users are not allowed to delete themselves"
            )

        session.delete(current_user)
        session.commit()
        return Message(message="User deleted successfully")

    @staticmethod
    def get_users(session: Session, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
        """
        获取用户列表（包含业务逻辑：分页、计数）
        """
        count_statement = select(func.count()).select_from(User)
        count = session.exec(count_statement).one()

        statement = select(User).offset(skip).limit(limit)
        users = session.exec(statement).all()

        return list(users), count

    @staticmethod
    def get_user_by_id(
        session: Session, user_id: uuid.UUID, current_user: User
    ) -> User:
        """
        根据ID获取用户（包含业务逻辑：权限检查）
        """
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 业务逻辑：用户只能查看自己，或者超级用户可以查看所有
        if user == current_user:
            return user

        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )

        return user

    @staticmethod
    def assign_roles_to_user(
        session: Session, user_id: uuid.UUID, role_ids: list[uuid.UUID]
    ) -> None:
        """
        为用户分配角色（包含业务逻辑：验证用户和角色存在）
        """
        # 业务逻辑：验证用户存在
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 业务逻辑：验证所有角色是否存在
        for role_id in role_ids:
            role = crud.get_role_by_id(session=session, role_id=role_id)
            if not role:
                raise HTTPException(status_code=404, detail=f"Role {role_id} not found")

        crud.set_user_roles(session=session, user_id=user_id, role_ids=role_ids)

    @staticmethod
    def assign_role_to_user(
        session: Session, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> None:
        """
        为用户添加单个角色（包含业务逻辑：验证存在性、防止重复）
        """
        from app.models import UserRole

        # 业务逻辑：验证用户存在
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 业务逻辑：验证角色存在
        role = crud.get_role_by_id(session=session, role_id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # 业务逻辑：检查是否已存在
        statement = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        existing = session.exec(statement).first()
        if existing:
            raise HTTPException(status_code=400, detail="Role already assigned to user")

        crud.assign_role_to_user(session=session, user_id=user_id, role_id=role_id)

    @staticmethod
    def remove_role_from_user(
        session: Session, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> None:
        """
        从用户移除角色（包含业务逻辑：验证用户存在）
        """
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        crud.remove_role_from_user(session=session, user_id=user_id, role_id=role_id)

    @staticmethod
    def get_user_roles(session: Session, user_id: uuid.UUID) -> list:
        """
        获取用户的所有角色（包含业务逻辑：验证用户存在）
        """
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return crud.get_user_roles(session=session, user_id=user_id)

