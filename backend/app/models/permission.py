from __future__ import annotations

from sqlmodel import Field, SQLModel


# ============================================
# Permission (权限/菜单) 相关模型 - 由 Menu 重构而来
# ============================================
class PermissionBase(SQLModel):
    key: str = Field(max_length=100)
    title: str = Field(max_length=200)
    url: str | None = Field(default=None, max_length=500)
    parent_id: int | None = Field(default=None)  # 不使用外键约束
    icon: str | None = Field(default=None, max_length=100)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(SQLModel):
    key: str | None = Field(default=None, max_length=100)
    title: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=500)
    parent_id: int | None = Field(default=None)
    icon: str | None = Field(default=None, max_length=100)
    sort_order: int | None = Field(default=None)
    is_active: bool | None = Field(default=None)


# Database model
class Permission(PermissionBase, table=True):
    __tablename__ = "permission"
    
    id: int = Field(primary_key=True)


# Properties to return via API
class PermissionPublic(PermissionBase):
    id: int
    parent_id: int | None = None
    children: list["PermissionPublic"] | None = None


class PermissionsPublic(SQLModel):
    data: list[PermissionPublic]
    count: int

