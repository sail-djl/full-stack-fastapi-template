from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.crud import (
    create_menu,
    delete_menu,
    get_menu_by_id,
    get_menu_by_key,
    get_menu_tree,
    update_menu,
)
from app.models import Menu, MenuCreate, MenuPublic, MenuUpdate, MenusPublic, Message


router = APIRouter(prefix="/menu", tags=["menu"])


def build_menu_tree(menus: list[Menu]) -> list[MenuPublic]:
    """将扁平菜单列表构建为树形结构"""
    # 创建菜单字典，初始化 children 为空列表
    menu_dict: dict[int, MenuPublic] = {}
    for menu in menus:
        menu_public = MenuPublic.model_validate(menu)
        menu_public.children = []
        menu_dict[menu.id] = menu_public
    
    root_menus = []
    
    # 构建树形结构
    for menu in menus:
        menu_public = menu_dict[menu.id]
        if menu.parent_id is None:
            root_menus.append(menu_public)
        else:
            parent = menu_dict.get(menu.parent_id)
            if parent and parent.children is not None:
                parent.children.append(menu_public)
    
    # 对每个菜单的子菜单进行排序
    def sort_children(menu: MenuPublic):
        if menu.children:
            menu.children.sort(key=lambda x: (x.sort_order, x.id))
            for child in menu.children:
                sort_children(child)
        else:
            # 如果没有子菜单，设置为 None（而不是空列表）
            menu.children = None
    
    for menu in root_menus:
        sort_children(menu)
    
    root_menus.sort(key=lambda x: (x.sort_order, x.id))
    return root_menus


@router.get("/tree", response_model=list[MenuPublic])
def get_menu_tree_api(session: SessionDep) -> Any:
    """
    获取菜单树（只返回启用的菜单，已构建为树形结构）
    """
    menus = get_menu_tree(session=session)
    menu_tree = build_menu_tree(menus)
    return menu_tree


@router.get("/", response_model=MenusPublic)
def read_menus(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> Any:
    """
    获取所有菜单（扁平列表，用于管理界面）
    """
    count_statement = select(func.count()).select_from(Menu)
    count = session.exec(count_statement).one()
    statement = select(Menu).offset(skip).limit(limit).order_by(Menu.sort_order, Menu.id)
    menus = session.exec(statement).all()
    return MenusPublic(data=[MenuPublic.model_validate(menu) for menu in menus], count=count)


@router.get("/{id}", response_model=MenuPublic)
def read_menu(session: SessionDep, id: int) -> Any:
    """
    根据ID获取菜单
    """
    menu = get_menu_by_id(session=session, menu_id=id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    return MenuPublic.model_validate(menu)


@router.post("/", response_model=MenuPublic)
def create_menu_api(
    *, session: SessionDep, menu_in: MenuCreate
) -> Any:
    """
    创建新菜单
    """
    # 检查 key 是否已存在
    existing_menu = get_menu_by_key(session=session, key=menu_in.key)
    if existing_menu:
        raise HTTPException(status_code=400, detail="Menu with this key already exists")
    
    menu = create_menu(session=session, menu_in=menu_in)
    return MenuPublic.model_validate(menu)


@router.put("/{id}", response_model=MenuPublic)
def update_menu_api(
    *,
    session: SessionDep,
    id: int,
    menu_in: MenuUpdate,
) -> Any:
    """
    更新菜单
    """
    menu = get_menu_by_id(session=session, menu_id=id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    
    # 如果更新 key，检查新 key 是否已存在
    if menu_in.key and menu_in.key != menu.key:
        existing_menu = get_menu_by_key(session=session, key=menu_in.key)
        if existing_menu:
            raise HTTPException(status_code=400, detail="Menu with this key already exists")
    
    menu = update_menu(session=session, db_menu=menu, menu_in=menu_in)
    return MenuPublic.model_validate(menu)


@router.delete("/{id}")
def delete_menu_api(
    session: SessionDep, id: int
) -> Message:
    """
    删除菜单
    """
    menu = get_menu_by_id(session=session, menu_id=id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    delete_menu(session=session, menu_id=id)
    return Message(message="Menu deleted successfully")

