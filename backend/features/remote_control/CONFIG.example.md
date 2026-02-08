# OpenClaw Remote Control API 配置示例

## 环境变量配置

将以下内容添加到 `config/.env` 或 `config/.env.local`:

```bash
# ==================== OpenClaw Remote Control API ====================

# 启用 Remote Control API
OPENCLAW_ENABLED=true

# API 认证密钥（请替换为你自己生成的密钥）
# 生成命令: python -c "from features.remote_control.auth import generate_api_key; print(generate_api_key())"
OPENCLAW_API_KEY=Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi

# 会话超时时间（秒）
# 默认: 3600 (1小时)
# 建议: 3600-7200
OPENCLAW_SESSION_TIMEOUT=3600

# ==================== 可选配置 ====================

# 日志级别（可选）
# LOG_LEVEL=INFO

# 最大会话数（可选，未实现）
# MAX_SESSIONS=100

# 最大文档大小（可选，未实现）
# MAX_DOCUMENT_SIZE_MB=10
```

## 生成新的 API Key

```bash
cd backend
python -c "from features.remote_control.auth import generate_api_key; print('New API Key:', generate_api_key())"
```

## 安全建议

1. **不要使用默认 API Key** - 测试完成后立即更换
2. **保护 .env 文件** - 不要提交到 Git（已在 .gitignore 中）
3. **定期更换** - 建议每 3-6 个月更换一次
4. **限制访问** - 仅授权的 OpenClaw 实例使用

## 验证配置

```bash
cd backend
python -c "
import os
from dotenv import load_dotenv
load_dotenv('../config/.env')
print('✓ OPENCLAW_ENABLED:', os.getenv('OPENCLAW_ENABLED'))
print('✓ API Key configured:', bool(os.getenv('OPENCLAW_API_KEY')))
print('✓ Session timeout:', os.getenv('OPENCLAW_SESSION_TIMEOUT'))
"
```
