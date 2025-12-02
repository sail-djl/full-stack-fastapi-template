import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import (
    Item,
    ItemCreate,
    Permission,
    PermissionCreate,
    PermissionUpdate,
    Role,
    RoleCreate,
    RolePermission,
    RoleUpdate,
    User,
    UserCreate,
    UserRole,
    UserUpdate,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# ============================================
# Permission (权限/菜单) CRUD functions
# ============================================
def get_permission_tree(*, session: Session) -> list[Permission]:
    """获取所有启用的权限，按层级和排序返回"""
    statement = select(Permission).where(Permission.is_active == True).order_by(
        Permission.parent_id.asc().nullsfirst(), Permission.sort_order.asc(), Permission.id.asc()
    )
    permissions = session.exec(statement).all()
    return list(permissions)


def get_permission_by_id(*, session: Session, permission_id: int) -> Permission | None:
    """根据ID获取权限"""
    return session.get(Permission, permission_id)


def get_permission_by_key(*, session: Session, key: str) -> Permission | None:
    """根据key获取权限"""
    statement = select(Permission).where(Permission.key == key)
    return session.exec(statement).first()


def create_permission(*, session: Session, permission_in: PermissionCreate) -> Permission:
    """创建权限"""
    db_permission = Permission.model_validate(permission_in)
    session.add(db_permission)
    session.commit()
    session.refresh(db_permission)
    return db_permission


def update_permission(*, session: Session, db_permission: Permission, permission_in: PermissionUpdate) -> Permission:
    """更新权限"""
    permission_data = permission_in.model_dump(exclude_unset=True)
    db_permission.sqlmodel_update(permission_data)
    session.add(db_permission)
    session.commit()
    session.refresh(db_permission)
    return db_permission


def delete_permission(*, session: Session, permission_id: int) -> None:
    """删除权限（级联删除子权限）"""
    permission = session.get(Permission, permission_id)
    if permission:
        session.delete(permission)
        session.commit()


# ============================================
# Role (角色) CRUD functions
# ============================================
def create_role(*, session: Session, role_in: RoleCreate) -> Role:
    """创建角色"""
    db_role = Role.model_validate(role_in)
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    return db_role


def get_role_by_id(*, session: Session, role_id: uuid.UUID) -> Role | None:
    """根据ID获取角色"""
    return session.get(Role, role_id)


def get_role_by_code(*, session: Session, code: str) -> Role | None:
    """根据代码获取角色"""
    statement = select(Role).where(Role.code == code)
    return session.exec(statement).first()


def get_roles(*, session: Session, skip: int = 0, limit: int = 100) -> list[Role]:
    """获取所有角色"""
    statement = select(Role).offset(skip).limit(limit).order_by(Role.sort_order, Role.name)
    return list(session.exec(statement).all())


def update_role(*, session: Session, db_role: Role, role_in: RoleUpdate) -> Role:
    """更新角色"""
    role_data = role_in.model_dump(exclude_unset=True)
    db_role.sqlmodel_update(role_data)
    session.add(db_role)
    session.commit()
    session.refresh(db_role)
    return db_role


def delete_role(*, session: Session, role_id: uuid.UUID) -> None:
    """删除角色"""
    role = session.get(Role, role_id)
    if role:
        session.delete(role)
        session.commit()


# ============================================
# UserRole (用户角色关联) functions
# ============================================
def assign_role_to_user(*, session: Session, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole:
    """为用户分配角色"""
    user_role = UserRole(user_id=user_id, role_id=role_id)
    session.add(user_role)
    session.commit()
    session.refresh(user_role)
    return user_role


def remove_role_from_user(*, session: Session, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
    """移除用户的角色"""
    statement = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    user_role = session.exec(statement).first()
    if user_role:
        session.delete(user_role)
        session.commit()


def get_user_roles(*, session: Session, user_id: uuid.UUID) -> list[Role]:
    """获取用户的所有角色"""
    statement = (
        select(Role)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, Role.is_active == True)
        .order_by(Role.sort_order, Role.name)
    )
    return list(session.exec(statement).all())


def get_role_users(*, session: Session, role_id: uuid.UUID) -> list[User]:
    """获取角色的所有用户"""
    statement = (
        select(User)
        .join(UserRole, User.id == UserRole.user_id)
        .where(UserRole.role_id == role_id, User.is_active == True)
        .order_by(User.email)
    )
    return list(session.exec(statement).all())


def set_user_roles(*, session: Session, user_id: uuid.UUID, role_ids: list[uuid.UUID]) -> None:
    """设置用户的角色（替换所有现有角色）"""
    # 删除现有角色
    statement = select(UserRole).where(UserRole.user_id == user_id)
    existing_user_roles = session.exec(statement).all()
    for user_role in existing_user_roles:
        session.delete(user_role)
    
    # 添加新角色
    for role_id in role_ids:
        user_role = UserRole(user_id=user_id, role_id=role_id)
        session.add(user_role)
    
    session.commit()


# ============================================
# RolePermission (角色权限关联) functions
# ============================================
def assign_permission_to_role(*, session: Session, role_id: uuid.UUID, permission_id: int) -> RolePermission:
    """为角色分配权限"""
    role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
    session.add(role_permission)
    session.commit()
    session.refresh(role_permission)
    return role_permission


def remove_permission_from_role(*, session: Session, role_id: uuid.UUID, permission_id: int) -> None:
    """移除角色的权限"""
    statement = select(RolePermission).where(
        RolePermission.role_id == role_id, RolePermission.permission_id == permission_id
    )
    role_permission = session.exec(statement).first()
    if role_permission:
        session.delete(role_permission)
        session.commit()


def get_role_permissions(*, session: Session, role_id: uuid.UUID) -> list[Permission]:
    """获取角色的所有权限"""
    statement = (
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id == role_id, Permission.is_active == True)
        .order_by(Permission.sort_order, Permission.id)
    )
    return list(session.exec(statement).all())


def get_permission_roles(*, session: Session, permission_id: int) -> list[Role]:
    """获取权限的所有角色"""
    statement = (
        select(Role)
        .join(RolePermission, Role.id == RolePermission.role_id)
        .where(RolePermission.permission_id == permission_id, Role.is_active == True)
        .order_by(Role.sort_order, Role.name)
    )
    return list(session.exec(statement).all())


def set_role_permissions(*, session: Session, role_id: uuid.UUID, permission_ids: list[int]) -> None:
    """设置角色的权限（替换所有现有权限）"""
    # 删除现有权限
    statement = select(RolePermission).where(RolePermission.role_id == role_id)
    existing_role_permissions = session.exec(statement).all()
    for role_permission in existing_role_permissions:
        session.delete(role_permission)
    
    # 添加新权限
    for permission_id in permission_ids:
        role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
        session.add(role_permission)
    
    session.commit()


def get_user_permissions(*, session: Session, user_id: uuid.UUID) -> list[Permission]:
    """获取用户的所有权限（通过角色）"""
    statement = (
        select(Permission)
        .distinct()
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, Role.is_active == True, Permission.is_active == True)
        .order_by(Permission.sort_order, Permission.id)
    )
    return list(session.exec(statement).all())


def has_permission(*, session: Session, user_id: uuid.UUID, permission_key: str) -> bool:
    """检查用户是否有指定权限"""
    statement = (
        select(Permission)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(Role, RolePermission.role_id == Role.id)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user_id,
            Permission.key == permission_key,
            Role.is_active == True,
            Permission.is_active == True,
        )
    )
    permission = session.exec(statement).first()
    return permission is not None
