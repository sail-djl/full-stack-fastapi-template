"""
测试 Tushare Pro 配置是否正确加载
"""

import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from app.core.config import settings


def test_tushare_config():
    """测试 Tushare Pro 配置"""
    print("=" * 50)
    print("Tushare Pro 配置测试")
    print("=" * 50)
    
    # 检查配置项
    print(f"\nTUSHARE_TOKEN: {settings.TUSHARE_TOKEN[:10] + '...' if settings.TUSHARE_TOKEN else '未配置'}")
    print(f"TUSHARE_API_URL: {settings.TUSHARE_API_URL}")
    
    # 验证配置完整性
    if settings.TUSHARE_TOKEN:
        print("\n✓ Tushare Pro 配置完整")
        print(f"  - Token: 已配置（长度: {len(settings.TUSHARE_TOKEN)}）")
        print(f"  - API URL: {settings.TUSHARE_API_URL}")
        
        # 尝试初始化 Tushare Pro（需要安装 tushare）
        try:
            import tushare as ts
            pro = ts.pro_api("test")
            pro._DataApi__token = settings.TUSHARE_TOKEN
            pro._DataApi__http_url = settings.TUSHARE_API_URL
            print("\n✓ Tushare Pro 初始化成功")
        except ImportError:
            print("\n⚠ Tushare 库未安装，无法测试 API 初始化")
            print("  安装命令: pip install tushare")
        except Exception as e:
            print(f"\n✗ Tushare Pro 初始化失败: {e}")
    else:
        print("\n✗ Tushare Pro 配置不完整")
        print("  请在 .env 文件中配置 TUSHARE_TOKEN")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    test_tushare_config()



