import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


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