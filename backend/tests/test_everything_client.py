"""
测试 Everything API 连接
运行方式：python -m pytest backend/tests/test_everything_client.py -v
或者直接运行：python backend/tests/test_everything_client.py
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

# 加载环境变量
config_dir = os.path.join(project_root, 'config')
load_dotenv(os.path.join(config_dir, '.env'))
load_dotenv(os.path.join(config_dir, '.env.local'), override=True)

from backend.core.everything_client import EverythingClient


def test_connection():
    """测试 Everything 连接"""
    print("\n=== 测试 Everything 连接 ===")
    client = EverythingClient()
    
    print(f"配置信息:")
    print(f"  URL: {client.base_url}")
    print(f"  用户名: {client.username}")
    print(f"  超时时间: {client.timeout}秒")
    
    try:
        result = client.test_connection()
        if result:
            print("[OK] 连接成功！")
            return True
        else:
            print("[FAIL] 连接失败")
            return False
    except Exception as e:
        print(f"[ERROR] 连接异常: {e}")
        return False


def test_basic_search():
    """测试基础搜索"""
    print("\n=== 测试基础搜索 ===")
    client = EverythingClient()
    
    try:
        # 搜索 .docx 文件
        results = client.search("*.docx", max_results=5)
        print(f"找到 {len(results)} 个 .docx 文件:")
        for i, file in enumerate(results[:5], 1):
            print(f"  {i}. {file.get('name')} ({file.get('path')})")
        
        return len(results) > 0
    
    except Exception as e:
        print(f"[FAIL] 搜索失败: {e}")
        return False


def test_advanced_search():
    """测试高级搜索（带过滤）"""
    print("\n=== 测试高级搜索 ===")
    client = EverythingClient()
    
    try:
        # 搜索最近一周修改的文档和表格
        results = client.search_with_filters(
            keywords="",  # 不限关键词
            file_types=['.docx', '.xlsx'],
            date_range='lastweek',
            max_results=10
        )
        
        print(f"找到上周修改的 {len(results)} 个文档/表格:")
        for i, file in enumerate(results[:5], 1):
            print(f"  {i}. {file.get('name')}")
            print(f"     路径: {file.get('path')}")
            print(f"     大小: {file.get('size', 'N/A')} bytes")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 高级搜索失败: {e}")
        return False


def test_keyword_search():
    """测试关键词搜索"""
    print("\n=== 测试关键词搜索 ===")
    client = EverythingClient()
    
    keyword = input("请输入要搜索的关键词（回车跳过）: ").strip()
    if not keyword:
        print("[SKIP] 跳过关键词搜索")
        return True
    
    try:
        results = client.search_with_filters(
            keywords=keyword,
            file_types=['.docx', '.xlsx', '.pdf', '.md'],
            max_results=10
        )
        
        print(f"找到 {len(results)} 个包含 '{keyword}' 的文件:")
        for i, file in enumerate(results, 1):
            print(f"  {i}. {file.get('name')}")
            print(f"     {file.get('path')}")
        
        return True
    
    except Exception as e:
        print(f"[FAIL] 关键词搜索失败: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Everything API 客户端测试")
    print("=" * 60)
    
    # 运行测试
    tests = [
        ("连接测试", test_connection),
        ("基础搜索", test_basic_search),
        ("高级搜索", test_advanced_search),
        ("关键词搜索", test_keyword_search),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n[SUCCESS] 所有测试通过！Everything 集成成功！")
    else:
        print("\n[WARNING] 部分测试失败，请检查配置和 Everything 服务状态")
