from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


# ============================================
# Role (角色) 相关模型
# ============================================
class RoleBase(SQLModel):
    name: str = Field(unique=True, index=True, max_length=100)
    code: str = Field(unique=True, index=True, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = Field(default=None)
    sort_order: int | None = Field(default=None)


class Role(RoleBase, table=True):
    __tablename__ = "role"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class RolePublic(RoleBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RolesPublic(SQLModel):
    data: list[RolePublic]
    count: int

