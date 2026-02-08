## OpenClaw Remote Control API 快速测试

### 1. 健康检查
```bash
curl -H "X-API-Key: Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi" \
  http://localhost:5179/api/remote-control/health
```

### 2. 查看能力列表
```bash
curl -H "X-API-Key: Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi" \
  http://localhost:5179/api/remote-control/capabilities
```

### 3. 创建会话
```bash
curl -X POST -H "X-API-Key: Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi" \
  -H "Content-Type: application/json" \
  -d '{"session_name":"Test Session"}' \
  http://localhost:5179/api/remote-control/session/create
```

### 4. 创建文档
```bash
curl -X POST -H "X-API-Key: Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess_xxx","title":"测试文档","content":{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Hello World"}]}]}}' \
  http://localhost:5179/api/remote-control/document/create
```

### 5. 导出 DOCX
```bash
curl -H "X-API-Key: Fw7qu71eTRTxMo1F91oTOvczCe5ojOzi" \
  http://localhost:5179/api/remote-control/document/doc_xxx/export-docx \
  --output test.docx
```
