from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


# ============================================
# 关联表模型
# ============================================
class UserRole(SQLModel, table=True):
    __tablename__ = "user_role"
    
    user_id: uuid.UUID = Field(primary_key=True)
    role_id: uuid.UUID = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permission"
    
    role_id: uuid.UUID = Field(primary_key=True)
    permission_id: int = Field(primary_key=True)  # 改为 INTEGER 类型
    created_at: datetime = Field(default_factory=datetime.utcnow)

