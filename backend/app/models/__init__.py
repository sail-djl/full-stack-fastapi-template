# 统一导出所有模型，保持向后兼容
# 注意：导入顺序很重要，需要先导入基础模型，再导入有关系的模型
from app.models.common import (
    Message,
    Token,
    TokenPayload,
    NewPassword,
)
from app.models.user import (
    User,
    UserBase,
    UserCreate,
    UserPublic,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
    UsersPublic,
    UpdatePassword,
)
from app.models.item import (
    Item,
    ItemBase,
    ItemCreate,
    ItemPublic,
    ItemUpdate,
    ItemsPublic,
)
from app.models.permission import (
    Permission,
    PermissionBase,
    PermissionCreate,
    PermissionPublic,
    PermissionUpdate,
    PermissionsPublic,
)
from app.models.role import (
    Role,
    RoleBase,
    RoleCreate,
    RolePublic,
    RoleUpdate,
    RolesPublic,
)
from app.models.polarization import (
    Polarization,
    PolarizationBase,
    PolarizationCreate,
    PolarizationPublic,
    PolarizationUpdate,
    PolarizationsPublic,
    Deviation,
    DeviationBase,
    DeviationCreate,
    DeviationPublic,
    DeviationsPublic,
)
from app.models.relationships import (
    UserRole,
    RolePermission,
)

# 保持向后兼容，所有导入仍然有效
__all__ = [
    # User
    "User",
    "UserBase",
    "UserCreate",
    "UserPublic",
    "UserRegister",
    "UserUpdate",
    "UserUpdateMe",
    "UsersPublic",
    "UpdatePassword",
    # Item
    "Item",
    "ItemBase",
    "ItemCreate",
    "ItemPublic",
    "ItemUpdate",
    "ItemsPublic",
    # Permission
    "Permission",
    "PermissionBase",
    "PermissionCreate",
    "PermissionPublic",
    "PermissionUpdate",
    "PermissionsPublic",
    # Role
    "Role",
    "RoleBase",
    "RoleCreate",
    "RolePublic",
    "RoleUpdate",
    "RolesPublic",
    # Polarization
    "Polarization",
    "PolarizationBase",
    "PolarizationCreate",
    "PolarizationPublic",
    "PolarizationUpdate",
    "PolarizationsPublic",
    # Deviation
    "Deviation",
    "DeviationBase",
    "DeviationCreate",
    "DeviationPublic",
    "DeviationsPublic",
    # Relationships
    "UserRole",
    "RolePermission",
    # Common
    "Message",
    "Token",
    "TokenPayload",
    "NewPassword",
]

