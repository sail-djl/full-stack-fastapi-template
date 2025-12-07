"""认证相关业务逻辑服务"""
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Message, NewPassword, Token, User
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)


class AuthService:
    """认证业务逻辑服务"""

    @staticmethod
    def login(session: Session, form_data: OAuth2PasswordRequestForm) -> Token:
        """
        用户登录（包含业务逻辑）
        """
        # 认证用户
        user = crud.authenticate(
            session=session, email=form_data.username, password=form_data.password
        )
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        elif not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        # 生成访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return Token(
            access_token=security.create_access_token(
                user.id, expires_delta=access_token_expires
            )
        )

    @staticmethod
    def recover_password(session: Session, email: str) -> Message:
        """
        密码恢复（包含业务逻辑）
        """
        user = crud.get_user_by_email(session=session, email=email)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="The user with this email does not exist in the system.",
            )

        # 生成重置令牌
        password_reset_token = generate_password_reset_token(email=email)
        
        # 发送重置邮件
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
        return Message(message="Password recovery email sent")

    @staticmethod
    def reset_password(session: Session, body: NewPassword) -> Message:
        """
        重置密码（包含业务逻辑）
        """
        # 验证令牌
        email = verify_password_reset_token(token=body.token)
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")

        # 获取用户
        user = crud.get_user_by_email(session=session, email=email)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="The user with this email does not exist in the system.",
            )
        elif not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        # 更新密码
        hashed_password = get_password_hash(password=body.new_password)
        user.hashed_password = hashed_password
        session.add(user)
        session.commit()
        return Message(message="Password updated successfully")

    @staticmethod
    def get_password_recovery_html(session: Session, email: str) -> tuple[str, str]:
        """
        获取密码恢复 HTML 内容（用于测试/调试）
        """
        user = crud.get_user_by_email(session=session, email=email)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="The user with this username does not exist in the system.",
            )

        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )

        return email_data.html_content, email_data.subject





