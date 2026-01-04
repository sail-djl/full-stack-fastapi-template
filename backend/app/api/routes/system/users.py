import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import func, select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.models import (
    Message,
    RolePublic,
    UpdatePassword,
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """
    users, count = UserService.get_users(session=session, skip=skip, limit=limit)
    return UsersPublic(data=users, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=UserPublic
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = UserService.create_user(session=session, user_in=user_in)
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """
    user = UserService.update_user_me(session=session, user_in=user_in, current_user=current_user)
    return UserPublic.model_validate(user)


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    return UserService.update_password_me(session=session, body=body, current_user=current_user)


@router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    return UserService.delete_user_me(session=session, current_user=current_user)


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = UserService.register_user(session=session, user_in=user_in)
    return UserPublic.model_validate(user)


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = UserService.get_user_by_id(session=session, user_id=user_id, current_user=current_user)
    return UserPublic.model_validate(user)


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: CurrentUser,
) -> Any:
    """
    Update a user.
    """
    user = UserService.update_user(
        session=session, user_id=user_id, user_in=user_in, current_user=current_user
    )
    return UserPublic.model_validate(user)


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    return UserService.delete_user(session=session, user_id=user_id, current_user=current_user)


# ============================================
# User-Role (用户角色关联) 路由
# ============================================
@router.get("/{user_id}/roles", response_model=list[RolePublic])
def get_user_roles(user_id: uuid.UUID, session: SessionDep) -> Any:
    """
    获取用户的所有角色
    """
    roles = UserService.get_user_roles(session=session, user_id=user_id)
    return [RolePublic.model_validate(role) for role in roles]


@router.post(
    "/{user_id}/roles",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def assign_roles_to_user(
    user_id: uuid.UUID,
    role_ids: list[uuid.UUID],
    session: SessionDep,
) -> Any:
    """
    为用户分配角色（替换所有现有角色）
    """
    UserService.assign_roles_to_user(session=session, user_id=user_id, role_ids=role_ids)
    return Message(message="Roles assigned successfully")


@router.post(
    "/{user_id}/roles/{role_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def assign_role_to_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """
    为用户添加单个角色
    """
    UserService.assign_role_to_user(session=session, user_id=user_id, role_id=role_id)
    return Message(message="Role assigned successfully")


@router.delete(
    "/{user_id}/roles/{role_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=Message,
)
def remove_role_from_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """
    从用户移除角色
    """
    UserService.remove_role_from_user(session=session, user_id=user_id, role_id=role_id)
    return Message(message="Role removed successfully")

