# OpenClaw Remote Control API

> 为 OpenClaw 提供 HTTP API 控制 INF5 Fast Canvas 功能

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

## 📖 概述

Remote Control API 是 INF5 的扩展模块，提供 RESTful HTTP 接口，让 OpenClaw（开源自主 AI 助手）能够远程控制 Fast Canvas 的文档处理和 AI 功能。

**核心功能**：
- 🔐 API Key 认证
- 📄 文档导入/导出（DOCX ↔ Tiptap JSON）
- 🎨 智能公文格式转换
- 🤖 AI 功能（知识库问答、智能写作、文档审计）
- 💾 会话管理（隔离工作空间）

## 🚀 快速开始

### 1. 配置环境
编辑 `config/.env`：
```bash
OPENCLAW_ENABLED=true
OPENCLAW_API_KEY=your_secure_key_here
OPENCLAW_SESSION_TIMEOUT=3600
```

### 2. 启动服务
```bash
cd backend
python app.py
```

### 3. 测试 API
```bash
python tests/quick_test.py
```

## 📚 API 端点

**Base URL**: `http://localhost:5179/api/remote-control`

### 会话管理
- `POST /session/create` - 创建会话
- `GET /session/{id}/status` - 查询状态
- `POST /session/{id}/close` - 关闭会话

### 文档操作
- `POST /document/create` - 创建文档
- `POST /document/import-docx` - 导入 DOCX
- `GET /document/{id}/export-docx` - 导出标准格式
- `GET /document/{id}/export-smart-docx` - 导出智能公文格式
- `GET /document/{id}/content` - 获取内容
- `PUT /document/{id}/content` - 更新内容

### AI 功能
- `POST /ai/chat` - 知识库问答
- `POST /ai/smart-write` - 智能写作
- `POST /ai/audit` - 文档审计

详细文档：[API Documentation](../../../.gemini/antigravity/brain/1708385c-66cb-4f64-b304-d59dc73edd43/api_documentation.md)

## 💡 使用示例

### Python
```python
import requests

API_KEY = "your_api_key"
BASE_URL = "http://localhost:5179/api/remote-control"
headers = {"X-API-Key": API_KEY}

# 创建会话
session = requests.post(f"{BASE_URL}/session/create", headers=headers).json()
session_id = session["data"]["session_id"]

# 智能写作
content = requests.post(
    f"{BASE_URL}/ai/smart-write",
    headers=headers,
    json={"prompt": "撰写5G应用报告"}
).json()["data"]["content"]

# 创建并导出文档
doc = requests.post(
    f"{BASE_URL}/document/create",
    headers=headers,
    json={
        "session_id": session_id,
        "title": "5G报告",
        "content": {"type": "doc", "content": [...]}
    }
).json()
doc_id = doc["data"]["doc_id"]

# 导出智能格式
docx = requests.get(
    f"{BASE_URL}/document/{doc_id}/export-smart-docx",
    headers=headers
)
with open("report.docx", "wb") as f:
    f.write(docx.content)
```

### cURL
```bash
# 健康检查
curl -H "X-API-Key: your_key" \
  http://localhost:5179/api/remote-control/health

# 创建会话
curl -X POST \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"session_name":"My Task"}' \
  http://localhost:5179/api/remote-control/session/create
```

## 🧪 测试

### 单元测试
```bash
pytest tests/test_remote_control.py -v
```

### 快速验证
```bash
python tests/quick_test.py
```

## 📂 项目结构

```
backend/
├── features/remote_control/
│   ├── __init__.py
│   ├── auth.py              # API Key 认证
│   ├── session_manager.py   # 会话管理
│   ├── services.py          # 业务逻辑
│   └── routes.py            # HTTP 端点
├── tests/
│   ├── test_remote_control.py   # Pytest 测试
│   ├── quick_test.py           # 快速验证
│   └── api_test_commands.md    # 测试命令
├── app.py                   # 主应用（已注册 remote_control_bp）
└── DEPLOYMENT.md            # 部署指南
```

## 🔒 安全

- ✅ **API Key 认证** - 所有端点需要有效 API Key
- ✅ **会话隔离** - 每个会话独立工作空间
- ✅ **输入验证** - 严格的参数检查
- ✅ **错误处理** - 统一的错误响应
- ✅ **日志审计** - 所有操作记录到日志

**建议**：
- 定期更换 API Key
- 生产环境使用 HTTPS
- 限制访问 IP 白名单

## 📖 文档

- [API 完整文档](../../../.gemini/antigravity/brain/1708385c-66cb-4f64-b304-d59dc73edd43/api_documentation.md) - 所有端点详细说明
- [部署指南](DEPLOYMENT.md) - 生产环境部署
- [实施总结](../../../.gemini/antigravity/brain/1708385c-66cb-4f64-b304-d59dc73edd43/walkthrough.md) - 开发过程和测试结果

## 🐛 故障排除

### 常见问题

**Q: API Key 错误？**  
A: 检查 `config/.env` 中的 `OPENCLAW_API_KEY` 配置

**Q: 导入 DOCX 失败？**  
A: 确认文件格式为 `.docx`，查看 `backend_debug.log` 获取详细错误

**Q: 会话超时？**  
A: 增加 `OPENCLAW_SESSION_TIMEOUT` 值（默认 3600 秒）

详细故障排除：[DEPLOYMENT.md](DEPLOYMENT.md#故障排除)

## 🤝 OpenClaw 集成

在 OpenClaw 中配置 INF5 API：

```python
# OpenClaw 自定义工具
def generate_report(topic):
    inf5_api = "http://your-server:5179/api/remote-control"
    api_key = "your_api_key"
    
    # 1. 创建会话
    session = create_session(inf5_api, api_key)
    
    # 2. 智能写作
    content = smart_write(inf5_api, api_key, f"撰写{topic}报告")
    
    # 3. 导出文档
    doc_id = create_document(inf5_api, api_key, session, content)
    export_docx(inf5_api, api_key, doc_id, "smart")
```

## 📊 技术栈

- **Web 框架**: Flask
- **认证**: API Key (Header-based)
- **文档转换**: python-docx
- **AI**: AnythingLLM 集成
- **测试**: Pytest, Requests

## 📝 更新日志

### v1.0.0 (2026-02-08)
- ✨ 初始发布
- ✅ 15+ API 端点
- ✅ 完整的会话管理
- ✅ 文档导入/导出（普通/智能格式）
- ✅ AI 功能集成
- ✅ 完整测试覆盖

## 📄 License

本项目是 INF5 的一部分，遵循相同的许可协议。

## 🙏 致谢

- OpenClaw 项目提供灵感
- INF5 团队提供基础设施
- AnythingLLM 提供 AI 能力

---

**Ready to use!** 查看 [API Documentation](../../../.gemini/antigravity/brain/1708385c-66cb-4f64-b304-d59dc73edd43/api_documentation.md) 开始使用。
