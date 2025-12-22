"""用户配置服务 - 管理用户配置的CRUD操作"""
from typing import Any, Optional
from datetime import datetime
from sqlalchemy import text
from sqlmodel import Session
import json


def _format_config_item(item: dict[str, Any]) -> dict[str, Any]:
    """格式化配置项：将UUID转换为字符串，JSONB转换为dict"""
    # 将UUID转换为字符串
    if item.get("user_id") is not None:
        item["user_id"] = str(item["user_id"])
    # 将JSONB转换为Python dict
    if isinstance(item.get("config_value"), str):
        try:
            item["config_value"] = json.loads(item["config_value"])
        except:
            item["config_value"] = {}
    return item


class UserConfigService:
    """用户配置服务"""

    @staticmethod
    def get_user_config_list(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        module: Optional[str] = None,
        config_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取用户配置列表
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        where: list[str] = ["TRUE"]

        if user_id:
            where.append("user_id = :user_id")
            params["user_id"] = user_id
        else:
            # 如果未指定user_id，查询所有配置（包括全局配置）
            pass

        if module:
            where.append("module = :module")
            params["module"] = module

        if config_type:
            where.append("config_type = :config_type")
            params["config_type"] = config_type

        if is_active is not None:
            where.append("is_active = :is_active")
            params["is_active"] = is_active

        where_sql = " AND ".join(where)

        sql_count = text(f"""
            SELECT COUNT(*) AS total
            FROM public.user_config
            WHERE {where_sql}
        """)
        total = int(session.execute(sql_count, params).scalar() or 0)

        sql_data = text(f"""
            SELECT 
                id,
                user_id,
                module,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at
            FROM public.user_config
            WHERE {where_sql}
            ORDER BY created_at DESC
            OFFSET :skip LIMIT :limit
        """)
        rows = session.execute(sql_data, params)
        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row._mapping)
            items.append(_format_config_item(item))

        return items, total

    @staticmethod
    def get_user_config_by_id(
        session: Session,
        config_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        根据ID获取用户配置
        """
        sql = text("""
            SELECT 
                id,
                user_id,
                module,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at
            FROM public.user_config
            WHERE id = :config_id
        """)
        row = session.execute(sql, {"config_id": config_id}).first()
        if not row:
            return None

        item = dict(row._mapping)
        return _format_config_item(item)

    @staticmethod
    def create_user_config(
        session: Session,
        user_id: Optional[str],
        module: Optional[str],
        config_type: str,
        config_key: str,
        config_value: dict[str, Any],
        is_active: bool = True,
        is_default: bool = False,
        description: Optional[str] = None,
        version: int = 1,
    ) -> dict[str, Any]:
        """
        创建用户配置
        """
        # 如果设置为默认配置，需要先取消同类型同用户的默认配置
        if is_default:
            sql_clear_default = text("""
                UPDATE public.user_config
                SET is_default = FALSE
                WHERE user_id = :user_id
                  AND config_type = :config_type
                  AND is_default = TRUE
            """)
            session.execute(
                sql_clear_default,
                {
                    "user_id": user_id,
                    "config_type": config_type,
                },
            )

        sql_insert = text("""
            INSERT INTO public.user_config (
                user_id,
                module,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version
            ) VALUES (
                :user_id,
                :module,
                :config_type,
                :config_key,
                CAST(:config_value AS jsonb),
                :is_active,
                :is_default,
                :description,
                :version
            )
            RETURNING 
                id,
                user_id,
                module,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at
        """)
        row = session.execute(
            sql_insert,
            {
                "user_id": user_id,
                "module": module,
                "config_type": config_type,
                "config_key": config_key,
                "config_value": json.dumps(config_value, ensure_ascii=False),
                "is_active": is_active,
                "is_default": is_default,
                "description": description,
                "version": version,
            },
        ).first()

        session.commit()

        item = dict(row._mapping)
        return _format_config_item(item)

    @staticmethod
    def update_user_config(
        session: Session,
        config_id: int,
        user_id: Optional[str] = None,
        module: Optional[str] = None,
        config_type: Optional[str] = None,
        config_key: Optional[str] = None,
        config_value: Optional[dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
        description: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """
        更新用户配置
        """
        # 先获取现有配置
        existing = UserConfigService.get_user_config_by_id(session, config_id)
        if not existing:
            return None

        # 如果设置为默认配置，需要先取消同类型同用户的默认配置
        if is_default is True:
            sql_clear_default = text("""
                UPDATE public.user_config
                SET is_default = FALSE
                WHERE user_id = :user_id
                  AND config_type = :config_type
                  AND id != :config_id
                  AND is_default = TRUE
            """)
            session.execute(
                sql_clear_default,
                {
                    "user_id": user_id or existing["user_id"],
                    "config_type": config_type or existing["config_type"],
                    "config_id": config_id,
                },
            )

        # 构建更新SQL
        updates: list[str] = []
        params: dict[str, Any] = {"config_id": config_id}

        if user_id is not None:
            updates.append("user_id = :user_id")
            params["user_id"] = user_id

        if module is not None:
            updates.append("module = :module")
            params["module"] = module

        if config_type is not None:
            updates.append("config_type = :config_type")
            params["config_type"] = config_type

        if config_key is not None:
            updates.append("config_key = :config_key")
            params["config_key"] = config_key

        if config_value is not None:
            updates.append("config_value = CAST(:config_value AS jsonb)")
            params["config_value"] = json.dumps(config_value, ensure_ascii=False)

        if is_active is not None:
            updates.append("is_active = :is_active")
            params["is_active"] = is_active

        if is_default is not None:
            updates.append("is_default = :is_default")
            params["is_default"] = is_default

        if description is not None:
            updates.append("description = :description")
            params["description"] = description

        if version is not None:
            updates.append("version = :version")
            params["version"] = version

        if not updates:
            return existing

        updates.append("updated_at = CURRENT_TIMESTAMP")

        sql_update = text(f"""
            UPDATE public.user_config
            SET {', '.join(updates)}
            WHERE id = :config_id
            RETURNING 
                id,
                user_id,
                module,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at
        """)
        row = session.execute(sql_update, params).first()

        session.commit()

        if not row:
            return None

        item = dict(row._mapping)
        return _format_config_item(item)

    @staticmethod
    def delete_user_config(
        session: Session,
        config_id: int,
    ) -> bool:
        """
        删除用户配置
        """
        sql = text("""
            DELETE FROM public.user_config
            WHERE id = :config_id
        """)
        result = session.execute(sql, {"config_id": config_id})
        session.commit()
        return result.rowcount > 0

    @staticmethod
    def get_default_config(
        session: Session,
        user_id: Optional[str],
        config_type: str,
    ) -> Optional[dict[str, Any]]:
        """
        获取用户的默认配置（优先用户配置，如果没有则返回全局默认配置）
        """
        # 先查询用户配置
        sql_user = text("""
            SELECT 
                id,
                user_id,
                module,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at
            FROM public.user_config
            WHERE user_id = :user_id
              AND config_type = :config_type
              AND is_default = TRUE
              AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = session.execute(
            sql_user, {"user_id": user_id, "config_type": config_type}
        ).first()

        if row:
            item = dict(row._mapping)
            return _format_config_item(item)

        # 如果没有用户配置，查询全局默认配置
        sql_global = text("""
            SELECT 
                id,
                user_id,
                module,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at
            FROM public.user_config
            WHERE user_id IS NULL
              AND config_type = :config_type
              AND is_default = TRUE
              AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = session.execute(sql_global, {"config_type": config_type}).first()

        if row:
            item = dict(row._mapping)
            return _format_config_item(item)

        return None

