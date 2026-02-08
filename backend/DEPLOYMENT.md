# OpenClaw Remote Control API - 部署指南

## 🚀 快速部署

### 前置要求
- Python 3.8+
- Git
- 已安装的依赖：`pip install -r backend/requirements.txt`

### 步骤 1: 拉取代码
```bash
cd /path/to/INFV5
git pull origin main
```

### 步骤 2: 配置环境变量
编辑 `config/.env` 文件，添加以下配置：

```bash
# OpenClaw Remote Control API
OPENCLAW_ENABLED=true
OPENCLAW_API_KEY=your_secure_api_key_here
OPENCLAW_SESSION_TIMEOUT=3600
```

**生成安全的 API Key**：
```bash
cd backend
python -c "from features.remote_control.auth import generate_api_key; print(generate_api_key())"
```

### 步骤 3: 启动服务
```bash
cd backend
python app.py
```

服务将在 `http://localhost:5179` 启动

### 步骤 4: 验证部署
```bash
cd backend
python tests/quick_test.py
```

如果看到 `=== All Tests Passed! ===`，说明部署成功！

---

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPENCLAW_ENABLED` | `false` | 启用/禁用 Remote Control API |
| `OPENCLAW_API_KEY` | - | API 认证密钥（必需）|
| `OPENCLAW_SESSION_TIMEOUT` | `3600` | 会话超时时间（秒）|

### 安全建议
1. **更换默认 API Key** - 不要使用测试 API Key
2. **限制访问** - 仅允许 OpenClaw 服务器 IP 访问
3. **HTTPS** - 生产环境使用 HTTPS
4. **日志监控** - 定期检查 `backend/backend_debug.log`

---

## 📦 文件清单

### 核心模块
- `backend/features/remote_control/__init__.py`
- `backend/features/remote_control/auth.py` - API Key 认证
- `backend/features/remote_control/session_manager.py` - 会话管理
- `backend/features/remote_control/services.py` - 业务逻辑
- `backend/features/remote_control/routes.py` - HTTP 端点

### 测试文件
- `backend/tests/test_remote_control.py` - Pytest 单元测试
- `backend/tests/quick_test.py` - 快速功能验证
- `backend/tests/api_test_commands.md` - cURL 测试命令

### 文档
- `api_documentation.md` - 完整 API 参考
- `deployment_guide.md` - 本文档
- `walkthrough.md` - 实施总结

---

## 🧪 测试

### 运行单元测试
```bash
cd backend
pytest tests/test_remote_control.py -v
```

### 快速功能测试
```bash
cd backend
python tests/quick_test.py
```

### 手动测试单个端点
```bash
# PowerShell
Invoke-WebRequest -Uri "http://localhost:5179/api/remote-control/health" `
  -Headers @{"X-API-Key"="your_api_key"} | Select-Object -Expand Content
```

---

## 🔍 故障排除

### 问题 1: 401 Unauthorized
**原因**: API Key 无效或未配置

**解决**:
```bash
# 检查配置
cat config/.env | grep OPENCLAW

# 确认配置正确
OPENCLAW_ENABLED=true
OPENCLAW_API_KEY=<your_key>
```

### 问题 2: ModuleNotFoundError
**原因**: 缺少依赖

**解决**:
```bash
cd backend
pip install -r requirements.txt
```

### 问题 3: 端口被占用
**原因**: 5179 端口已被使用

**解决**:
```bash
# 修改 backend/app.py 中的端口
# 或杀死占用进程
netstat -ano | findstr :5179
taskkill /PID <进程ID> /F
```

### 问题 4: 会话超时
**原因**: 长时间未活动

**解决**: 增加超时时间
```bash
# 在 .env 中设置
OPENCLAW_SESSION_TIMEOUT=7200  # 2小时
```

---

## 📊 监控和维护

### 日志位置
- **应用日志**: `backend/backend_debug.log`
- **包含内容**: API 调用、错误、会话管理

### 日志示例
```
2026-02-08 21:30:00 - INFO - API Key validated for remote_control.create_session
2026-02-08 21:30:01 - INFO - Created session: sess_abc123
2026-02-08 21:30:05 - INFO - Created document doc_xyz789 in session sess_abc123
```

### 定期维护
1. **清理过期会话** - 自动执行，每次访问时检查
2. **日志轮转** - 建议配置 logrotate
3. **监控磁盘** - 会话文档占用内存

---

## 🌐 生产部署建议

### 使用 Gunicorn（推荐）
```bash
# 安装
pip install gunicorn

# 启动
cd backend
gunicorn -w 4 -b 0.0.0.0:5179 app:app
```

### 使用 Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/remote-control {
        proxy_pass http://localhost:5179;
        proxy_set_header X-API-Key $http_x_api_key;
        proxy_set_header Host $host;
    }
}
```

### 使用 systemd 服务
```ini
# /etc/systemd/system/inf5-remote-api.service
[Unit]
Description=INF5 Remote Control API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/INFV5/backend
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:5179 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl start inf5-remote-api
sudo systemctl enable inf5-remote-api
```

---

## 📱 OpenClaw 配置示例

### 配置 API 端点
在 OpenClaw 中添加自定义工具：

```yaml
# openclaw-config.yaml
tools:
  - name: inf5_remote_control
    type: http_api
    base_url: http://your-server:5179/api/remote-control
    auth:
      type: header
      key: X-API-Key
      value: your_api_key_here
    endpoints:
      - create_session: POST /session/create
      - smart_write: POST /ai/smart-write
      - export_docx: GET /document/{doc_id}/export-smart-docx
```

---

## ✅ 部署检查清单

- [ ] 代码已拉取到最新版本
- [ ] `.env` 配置完成
- [ ] API Key 已生成并配置
- [ ] 依赖已安装
- [ ] 服务可以启动
- [ ] 快速测试通过
- [ ] OpenClaw 配置完成
- [ ] 生产环境启用 HTTPS
- [ ] 日志监控已配置

---

**部署完成后，您的 OpenClaw 即可通过 HTTP API 控制 INF5 的 Fast Canvas！** 🎉
