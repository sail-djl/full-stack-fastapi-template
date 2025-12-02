# Tushare Pro 配置使用说明

## 配置位置

Tushare Pro 的配置已经添加到 `app/core/config.py` 中的 `Settings` 类。

## 配置项

- `TUSHARE_TOKEN`: Tushare Pro API Token（从环境变量读取）
- `TUSHARE_API_URL`: Tushare Pro API 地址（默认：`http://pro.tushare.nlink.vip`）

## 环境变量配置

在项目根目录的 `.env` 文件中已添加：

```env
# ============================================
# Tushare Pro 配置
# ============================================
TUSHARE_TOKEN=b1i2r1j1j0eu2ev258
TUSHARE_API_URL=http://pro.tushare.nlink.vip
```

## 使用方法

### 在代码中使用配置

```python
from app.core.config import settings

# 获取配置
token = settings.TUSHARE_TOKEN
api_url = settings.TUSHARE_API_URL

# 初始化 Tushare Pro
if token:
    import tushare as ts
    pro = ts.pro_api("tushare_pro")
    pro._DataApi__token = token
    pro._DataApi__http_url = api_url
    
    # 使用 API
    df = pro.index_basic()
    print(df)
else:
    print("Tushare token 未配置")
```

### 在 API 路由中使用

```python
from fastapi import APIRouter, Depends
from app.core.config import settings
import tushare as ts

router = APIRouter()

def get_tushare_pro():
    """获取 Tushare Pro 实例"""
    if not settings.TUSHARE_TOKEN:
        raise ValueError("Tushare token 未配置")
    
    pro = ts.pro_api("tushare_pro")
    pro._DataApi__token = settings.TUSHARE_TOKEN
    pro._DataApi__http_url = settings.TUSHARE_API_URL
    return pro

@router.get("/index/basic")
def get_index_basic(pro = Depends(get_tushare_pro)):
    """获取指数基本信息"""
    df = pro.index_basic()
    return df.to_dict('records')
```

### 检查配置是否完整

```python
from app.core.config import settings

# 检查 token 是否配置
if settings.TUSHARE_TOKEN:
    print("✓ Tushare token 已配置")
else:
    print("✗ Tushare token 未配置")
```

## 安全注意事项

1. **不要将 `.env` 文件提交到版本控制**
   - 确保 `.env` 在 `.gitignore` 中
   - Token 是敏感信息，应该保密

2. **生产环境配置**
   - 使用环境变量而不是 `.env` 文件
   - 使用密钥管理服务（如 AWS Secrets Manager, Azure Key Vault）

3. **配置验证**
   - `TUSHARE_TOKEN` 是可选的（`str | None`），便于本地开发时可选配置
   - 在使用前检查 token 是否存在

## 相关文件

- 配置文件：`backend/app/core/config.py`
- 环境变量：`.env`（项目根目录）
- Token 源文件：`E:\finance\3.1 - Tushare Pro\1-token\token.txt`



