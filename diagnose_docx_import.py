#!/usr/bin/env python3
"""
DOCX 导入功能 - 一键部署和诊断脚本
运行此脚本将自动完成部署并测试 DOCX 导入功能
"""

import os
import sys
import subprocess
import requests
import json
from datetime import datetime
from pathlib import Path

# 配置
BACKEND_URL = "http://localhost:5000"
PROJECT_ROOT = Path(__file__).parent.absolute()

class Logger:
    """彩色日志输出"""
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'RED': '\033[91m',
        'END': '\033[0m',
        'BOLD': '\033[1m',
    }
    
    @staticmethod
    def header(msg):
        print(f"\n{Logger.COLORS['HEADER']}{Logger.COLORS['BOLD']}{'='*60}{Logger.COLORS['END']}")
        print(f"{Logger.COLORS['HEADER']}{Logger.COLORS['BOLD']}{msg}{Logger.COLORS['END']}")
        print(f"{Logger.COLORS['HEADER']}{Logger.COLORS['BOLD']}{'='*60}{Logger.COLORS['END']}\n")
    
    @staticmethod
    def info(msg):
        print(f"{Logger.COLORS['BLUE']}ℹ️  {msg}{Logger.COLORS['END']}")
    
    @staticmethod
    def success(msg):
        print(f"{Logger.COLORS['GREEN']}✅ {msg}{Logger.COLORS['END']}")
    
    @staticmethod
    def warning(msg):
        print(f"{Logger.COLORS['YELLOW']}⚠️  {msg}{Logger.COLORS['END']}")
    
    @staticmethod
    def error(msg):
        print(f"{Logger.COLORS['RED']}❌ {msg}{Logger.COLORS['END']}")
    
    @staticmethod
    def step(num, msg):
        print(f"\n{Logger.COLORS['BOLD']}步骤 {num}: {msg}{Logger.COLORS['END']}")

def run_command(cmd, cwd=None, check=True):
    """执行系统命令并返回输出"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or PROJECT_ROOT,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        if check and result.returncode != 0:
            Logger.error(f"命令执行失败: {cmd}")
            Logger.error(f"错误输出: {result.stderr}")
            return None
        return result
    except subprocess.TimeoutExpired:
        Logger.error(f"命令超时: {cmd}")
        return None
    except Exception as e:
        Logger.error(f"命令执行异常: {e}")
        return None

def check_git_status():
    """检查 Git 状态"""
    Logger.step(1, "检查 Git 仓库状态")
    
    # 检查是否在正确的目录
    if not (PROJECT_ROOT / '.git').exists():
        Logger.error(f"当前目录不是 Git 仓库: {PROJECT_ROOT}")
        return False
    
    # 获取当前分支
    result = run_command("git branch --show-current")
    if result:
        branch = result.stdout.strip()
        Logger.info(f"当前分支: {branch}")
    
    # 获取最新提交
    result = run_command("git log -1 --oneline")
    if result:
        Logger.info(f"当前提交: {result.stdout.strip()}")
    
    return True

def deploy_latest_code():
    """拉取最新代码"""
    Logger.step(2, "拉取最新代码")
    
    # 获取远程更新
    Logger.info("正在获取远程更新...")
    result = run_command("git fetch origin")
    if not result:
        return False
    
    # 检查是否有未提交的更改
    result = run_command("git status --porcelain")
    if result and result.stdout.strip():
        Logger.warning("检测到未提交的本地更改")
        print(result.stdout)
        response = input("是否要暂存这些更改并继续? (y/n): ")
        if response.lower() == 'y':
            run_command("git stash")
            Logger.info("已暂存本地更改")
        else:
            Logger.error("部署已取消")
            return False
    
    # 拉取最新代码
    Logger.info("正在拉取最新代码...")
    result = run_command("git pull origin main")
    if not result:
        return False
    
    if "Already up to date" in result.stdout:
        Logger.success("代码已是最新版本")
    else:
        Logger.success("代码更新成功")
        print(result.stdout)
    
    # 显示最新的提交
    result = run_command("git log -1 --oneline")
    if result:
        Logger.info(f"最新提交: {result.stdout.strip()}")
    
    return True

def check_backend_service():
    """检查后端服务状态"""
    Logger.step(3, "检查后端服务")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            Logger.success(f"后端服务运行正常 ({BACKEND_URL})")
            return True
    except requests.exceptions.ConnectionError:
        Logger.error("后端服务未响应")
    except requests.exceptions.Timeout:
        Logger.error("后端服务响应超时")
    except Exception as e:
        Logger.error(f"检查后端服务时出错: {e}")
    
    Logger.warning("请手动重启后端服务:")
    Logger.info("  方法1: cd backend && python app.py")
    Logger.info("  方法2: systemctl restart infv5-backend")
    
    response = input("\n是否已重启后端服务? (y/n): ")
    return response.lower() == 'y'

def test_docx_import():
    """测试 DOCX 导入功能"""
    Logger.step(4, "测试 DOCX 导入功能")
    
    # 创建测试 DOCX 文件
    Logger.info("创建测试 DOCX 文件...")
    try:
        from docx import Document
        
        doc = Document()
        doc.add_heading('测试文档', 0)
        doc.add_paragraph('这是第一段测试文本。')
        doc.add_paragraph('这是第二段测试文本，包含一些**粗体**内容。')
        
        # 添加表格
        table = doc.add_table(rows=2, cols=2)
        table.rows[0].cells[0].text = '列1'
        table.rows[0].cells[1].text = '列2'
        table.rows[1].cells[0].text = '数据1'
        table.rows[1].cells[1].text = '数据2'
        
        test_file = PROJECT_ROOT / 'test_docx_import.docx'
        doc.save(test_file)
        Logger.success(f"测试文件已创建: {test_file}")
    except ImportError:
        Logger.error("需要安装 python-docx: pip install python-docx")
        return False
    except Exception as e:
        Logger.error(f"创建测试文件失败: {e}")
        return False
    
    # 测试导入 API
    Logger.info("调用后端导入 API...")
    try:
        with open(test_file, 'rb') as f:
            files = {'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(
                f"{BACKEND_URL}/api/canvas/import-from-docx",
                files=files,
                timeout=10
            )
        
        Logger.info(f"HTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            Logger.success("导入成功!")
            
            # 分析返回数据
            content = data.get('content', [])
            Logger.info(f"解析出 {len(content)} 个内容节点")
            
            # 检查空文本节点
            empty_nodes = []
            def check_nodes(nodes, path=""):
                for i, node in enumerate(nodes):
                    node_path = f"{path}[{i}]"
                    if node.get('type') == 'text' and not node.get('text'):
                        empty_nodes.append(node_path)
                    if 'content' in node:
                        check_nodes(node['content'], f"{node_path}.content")
            
            check_nodes(content)
            
            if empty_nodes:
                Logger.warning(f"发现 {len(empty_nodes)} 个空文本节点（应由前端清洗）:")
                for path in empty_nodes[:5]:  # 只显示前5个
                    Logger.warning(f"  - {path}")
            else:
                Logger.success("未发现空文本节点 - 数据质量良好")
            
            # 显示示例内容
            Logger.info("\n返回数据示例 (前3个节点):")
            print(json.dumps(content[:3], indent=2, ensure_ascii=False))
            
            return True
        else:
            Logger.error(f"导入失败: {response.status_code}")
            Logger.error(f"错误信息: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        Logger.error("无法连接到后端服务")
        return False
    except Exception as e:
        Logger.error(f"测试导入时出错: {e}")
        return False
    finally:
        # 清理测试文件
        if test_file.exists():
            test_file.unlink()

def check_frontend_files():
    """检查关键前端文件是否存在修复"""
    Logger.step(5, "验证前端修复文件")
    
    checks = {
        'frontend/src/features/fast-canvas/FastCanvasView.tsx': 'sanitizeContent',
        'frontend/src/features/fast-canvas/components/Editor/TiptapEditor.css': '--tw-prose-body',
        'backend/features/canvas_converter.py': 'fallback'
    }
    
    all_ok = True
    for file_path, keyword in checks.items():
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            Logger.error(f"文件不存在: {file_path}")
            all_ok = False
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if keyword in content:
                Logger.success(f"✓ {file_path} 包含修复: {keyword}")
            else:
                Logger.warning(f"✗ {file_path} 可能未包含修复: {keyword}")
                all_ok = False
    
    return all_ok

def generate_summary(results):
    """生成诊断摘要"""
    Logger.header("诊断摘要")
    
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目路径: {PROJECT_ROOT}")
    print(f"后端地址: {BACKEND_URL}")
    print()
    
    status_map = {
        'git': results.get('git', False),
        'deploy': results.get('deploy', False),
        'backend': results.get('backend', False),
        'frontend': results.get('frontend', False),
        'import': results.get('import', False),
    }
    
    for key, status in status_map.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {key.upper()}: {'通过' if status else '失败'}")
    
    all_passed = all(status_map.values())
    
    if all_passed:
        Logger.header("🎉 所有检查通过！DOCX 导入功能正常")
        Logger.info("您现在可以在浏览器中使用 DOCX 导入功能了")
        Logger.info("如仍有问题，请清除浏览器缓存 (Ctrl+F5)")
    else:
        Logger.header("⚠️  部分检查未通过")
        Logger.info("请将此日志输出发送给开发者以获得帮助")

def main():
    """主函数"""
    Logger.header("DOCX 导入功能 - 自动部署和诊断")
    
    results = {}
    
    # 检查 Git 状态
    results['git'] = check_git_status()
    if not results['git']:
        Logger.error("Git 检查失败，请确保在项目根目录运行此脚本")
        return 1
    
    # 部署最新代码
    results['deploy'] = deploy_latest_code()
    if not results['deploy']:
        Logger.error("代码部署失败")
        return 1
    
    # 检查后端服务
    results['backend'] = check_backend_service()
    if not results['backend']:
        Logger.error("后端服务检查失败")
        return 1
    
    # 验证前端文件
    results['frontend'] = check_frontend_files()
    
    # 测试 DOCX 导入
    results['import'] = test_docx_import()
    
    # 生成摘要
    generate_summary(results)
    
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        Logger.warning("\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        Logger.error(f"\n未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
