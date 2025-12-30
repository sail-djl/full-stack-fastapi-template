"""系统配置服务 - 管理系统配置的CRUD操作"""
from typing import Any, Optional
from sqlalchemy import text
from sqlmodel import Session
import json


def _format_config_item(item: dict[str, Any]) -> dict[str, Any]:
    """格式化配置项：将UUID转换为字符串，JSONB转换为dict"""
    # 将JSONB转换为Python dict
    if isinstance(item.get("config_value"), str):
        try:
            item["config_value"] = json.loads(item["config_value"])
        except:
            item["config_value"] = {}
    
    # 将created_by和updated_by转换为字符串（如果是UUID）
    if item.get("created_by") is not None:
        item["created_by"] = str(item["created_by"])
    if item.get("updated_by") is not None:
        item["updated_by"] = str(item["updated_by"])
    
    return item


class SystemConfigService:
    """系统配置服务"""

    @staticmethod
    def get_system_config_list(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        config_category: Optional[str] = None,
        config_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        获取系统配置列表
        """
        params: dict[str, Any] = {"skip": skip, "limit": limit}
        where: list[str] = ["TRUE"]

        if config_category:
            where.append("config_category = :config_category")
            params["config_category"] = config_category

        if config_type:
            where.append("config_type = :config_type")
            params["config_type"] = config_type

        if is_active is not None:
            where.append("is_active = :is_active")
            params["is_active"] = is_active

        if is_default is not None:
            where.append("is_default = :is_default")
            params["is_default"] = is_default

        where_sql = " AND ".join(where)

        sql_count = text(f"""
            SELECT COUNT(*) AS total
            FROM public.system_config
            WHERE {where_sql}
        """)
        total = int(session.execute(sql_count, params).scalar() or 0)

        sql_data = text(f"""
            SELECT 
                id,
                config_category,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at,
                created_by,
                updated_by
            FROM public.system_config
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
    def get_system_config_by_id(
        session: Session,
        config_id: int,
    ) -> Optional[dict[str, Any]]:
        """
        根据ID获取系统配置
        """
        sql = text("""
            SELECT 
                id,
                config_category,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at,
                created_by,
                updated_by
            FROM public.system_config
            WHERE id = :config_id
        """)
        row = session.execute(sql, {"config_id": config_id}).first()
        if not row:
            return None

        item = dict(row._mapping)
        return _format_config_item(item)

    @staticmethod
    def create_system_config(
        session: Session,
        config_category: str,
        config_type: str,
        config_key: str,
        config_value: dict[str, Any],
        is_active: bool = True,
        is_default: bool = False,
        description: Optional[str] = None,
        version: int = 1,
        created_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        创建系统配置
        """
        # 如果设置为默认配置，需要先取消同分类同类型的默认配置
        if is_default:
            sql_clear_default = text("""
                UPDATE public.system_config
                SET is_default = FALSE
                WHERE config_category = :config_category
                  AND config_type = :config_type
                  AND is_default = TRUE
            """)
            session.execute(
                sql_clear_default,
                {
                    "config_category": config_category,
                    "config_type": config_type,
                },
            )

        sql_insert = text("""
            INSERT INTO public.system_config (
                config_category,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_by
            ) VALUES (
                :config_category,
                :config_type,
                :config_key,
                CAST(:config_value AS jsonb),
                :is_active,
                :is_default,
                :description,
                :version,
                :created_by
            )
            RETURNING 
                id,
                config_category,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at,
                created_by,
                updated_by
        """)
        row = session.execute(
            sql_insert,
            {
                "config_category": config_category,
                "config_type": config_type,
                "config_key": config_key,
                "config_value": json.dumps(config_value, ensure_ascii=False),
                "is_active": is_active,
                "is_default": is_default,
                "description": description,
                "version": version,
                "created_by": created_by,
            },
        ).first()

        session.commit()

        item = dict(row._mapping)
        return _format_config_item(item)

    @staticmethod
    def update_system_config(
        session: Session,
        config_id: int,
        config_category: Optional[str] = None,
        config_type: Optional[str] = None,
        config_key: Optional[str] = None,
        config_value: Optional[dict[str, Any]] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None,
        description: Optional[str] = None,
        version: Optional[int] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        更新系统配置
        """
        # 先获取现有配置
        existing = SystemConfigService.get_system_config_by_id(session, config_id)
        if not existing:
            return None

        # 如果设置为默认配置，需要先取消同分类同类型的默认配置
        if is_default is True:
            final_category = config_category or existing["config_category"]
            final_type = config_type or existing["config_type"]
            sql_clear_default = text("""
                UPDATE public.system_config
                SET is_default = FALSE
                WHERE config_category = :config_category
                  AND config_type = :config_type
                  AND id != :config_id
                  AND is_default = TRUE
            """)
            session.execute(
                sql_clear_default,
                {
                    "config_category": final_category,
                    "config_type": final_type,
                    "config_id": config_id,
                },
            )

        # 构建更新SQL
        updates: list[str] = []
        params: dict[str, Any] = {"config_id": config_id}

        if config_category is not None:
            updates.append("config_category = :config_category")
            params["config_category"] = config_category

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

        if updated_by is not None:
            updates.append("updated_by = :updated_by")
            params["updated_by"] = updated_by

        if not updates:
            return existing

        updates.append("updated_at = CURRENT_TIMESTAMP")

        sql_update = text(f"""
            UPDATE public.system_config
            SET {', '.join(updates)}
            WHERE id = :config_id
            RETURNING 
                id,
                config_category,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at,
                created_by,
                updated_by
        """)
        row = session.execute(sql_update, params).first()

        session.commit()

        if not row:
            return None

        item = dict(row._mapping)
        return _format_config_item(item)

    @staticmethod
    def delete_system_config(
        session: Session,
        config_id: int,
    ) -> bool:
        """
        删除系统配置
        """
        sql = text("""
            DELETE FROM public.system_config
            WHERE id = :config_id
        """)
        result = session.execute(sql, {"config_id": config_id})
        session.commit()
        return result.rowcount > 0

    @staticmethod
    def get_default_config(
        session: Session,
        config_category: str,
        config_type: str,
    ) -> Optional[dict[str, Any]]:
        """
        获取默认配置
        """
        sql = text("""
            SELECT 
                id,
                config_category,
                config_type,
                config_key,
                config_value,
                is_active,
                is_default,
                description,
                version,
                created_at::text as created_at,
                updated_at::text as updated_at,
                created_by,
                updated_by
            FROM public.system_config
            WHERE config_category = :config_category
              AND config_type = :config_type
              AND is_default = TRUE
              AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = session.execute(
            sql, {"config_category": config_category, "config_type": config_type}
        ).first()

        if row:
            item = dict(row._mapping)
            return _format_config_item(item)

        return None

