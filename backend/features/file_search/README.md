# 文件搜索 API 使用文档

## 📡 API 端点

### 1. 智能搜索 (Smart Search)

**端点**: `POST /api/file-search/search`

**描述**: 使用 Everything + AI 智能排序进行文件搜索

**请求体**:
```json
{
  "query": "智慧城市",
  "fileTypes": [".docx", ".xlsx"],
  "dateRange": "lastweek",
  "maxResults": 10,
  "enableAiRanking": true
}
```

**参数说明**:
- `query` (必填): 搜索关键词
- `fileTypes` (可选): 文件类型过滤，例如 `[".docx", ".xlsx", ".pdf"]`
- `dateRange` (可选): 时间范围，可选值：`today`, `yesterday`, `lastweek`, `lastmonth`, `lastyear`
- `maxResults` (可选): 最多返回结果数，默认 10，最大 100
- `enableAiRanking` (可选): 是否启用 AI 排序，默认 `true`

**响应示例**:
```json
{
  "success": true,
  "query": "智慧城市",
  "total": 5,
  "results": [
    {
      "name": "智慧城市方案.docx",
      "path": "D:\\Projects\\智慧城市方案.docx",
      "size": 102400,
      "date_modified": "2024-01-15 14:30:00",
      "ai_score": 95.5,
      "ai_reason": "文件名与'智慧城市'高度匹配；路径相关性高",
      "is_recommended": true
    }
  ]
}
```

---

### 2. 快速搜索 (Quick Search)

**端点**: `GET /api/file-search/quick-search?q=关键词&limit=10`

**描述**: 快速搜索（不启用 AI 排序，速度更快）

**参数**:
- `q`: 搜索关键词
- `limit`: 最多返回结果数，默认 10

**示例**:
```
GET /api/file-search/quick-search?q=预算&limit=5
```

---

### 3. 搜索文档 (Search Documents)

**端点**: `POST /api/file-search/search/documents`

**描述**: 搜索文档类型文件（.docx, .pdf, .md, .txt）

**请求体**:
```json
{
  "query": "项目报告",
  "maxResults": 10
}
```

---

### 4. 搜索表格 (Search Spreadsheets)

**端点**: `POST /api/file-search/search/spreadsheets`

**描述**: 搜索表格类型文件（.xlsx, .xls, .csv）

**请求体**:
```json
{
  "query": "销售数据",
  "maxResults": 10
}
```

---

### 5. 健康检查 (Health Check)

**端点**: `GET /api/file-search/health`

**描述**: 检查 Everything 服务状态

**响应示例**:
```json
{
  "status": "ok",
  "everything_connected": true,
  "message": "Everything service is running"
}
```

---

## 🧪 测试步骤

### 前置条件

⚠️ **必须确保 Everything HTTP 服务正在运行**

1. 打开 Everything
2. 工具 → 选项 → HTTP 服务器
3. 确认以下配置：
   - ✅ 启用 HTTP 服务器
   - 端口：292
   - 用户名：yc
   - 密码：（已配置）

### 测试 1：健康检查

```bash
curl http://localhost:5179/api/file-search/health
```

**预期结果**: 
```json
{
  "status": "ok",
  "everything_connected": true
}
```

如果返回 `everything_connected: false`，说明 Everything 服务未启动或配置错误。

---

### 测试 2：快速搜索

```bash
curl "http://localhost:5179/api/file-search/quick-search?q=.docx&limit=3"
```

---

### 测试 3：智能搜索

使用 Python 测试：

```python
import requests

url = "http://localhost:5179/api/file-search/search"
payload = {
    "query": "测试",
    "fileTypes": [".txt", ".md"],
    "maxResults": 5
}

response = requests.post(url, json=payload)
print(response.json())
```

---

### 测试 4：搜索文档

```python
import requests

url = "http://localhost:5179/api/file-search/search/documents"
payload = {
    "query": "项目",
    "maxResults": 10
}

response = requests.post(url, json=payload)
results = response.json()

print(f"找到 {results['total']} 个文档")
for file in results['results'][:5]:
    print(f"  - {file['name']}")
    if file.get('is_recommended'):
        print(f"    推荐理由: {file['ai_reason']}")
```

---

## 🔧 Everything 查询语法参考

Everything 支持强大的搜索语法：

```
# 基础关键词
智慧城市

# 文件类型
*.docx
*.xlsx|*.xls

# 时间过滤
dm:today        # 今天修改
dm:lastweek     # 上周修改
dm:lastmonth    # 上月修改
dc:2024         # 2024 年创建

# 大小过滤
size:>1mb       # 大于 1MB
size:<100kb     # 小于 100KB

# 组合查询
智慧城市 *.pptx dm:lastweek
```

---

## ⚠️ 疑难排查

### 问题 1: 连接失败

**症状**: `Cannot connect to Everything HTTP server`

**解决方案**:
1. 确认 Everything 正在运行
2. 确认 HTTP 服务器已启用（工具 → 选项 → HTTP 服务器）
3. 确认端口号正确（默认 292）
4. 检查防火墙设置

---

### 问题 2: 认证失败

**症状**: `401 Unauthorized`

**解决方案**:
1. 检查 `.env.local` 中的用户名和密码
2. 确认 Everything 中设置的用户名密码与配置文件一致

---

### 问题 3: 搜索无结果

**症状**: `total: 0`

**可能原因**:
1. 查询关键词不存在
2. 文件类型过滤太严格
3. Everything 索引未完成

**解决方案**:
1. 尝试更通用的关键词，如 `*.*` 搜索所有文件
2. 去掉文件类型和时间过滤
3. 等待 Everything 建立索引（通常很快）

---

## 📝 Agent 工具使用

Agent 可以自动调用文件搜索工具。

**用户提问示例**:
- "帮我找一下关于智慧城市的文档"
- "上周修改的预算表在哪里"
- "有没有关于 AI 培训的 PPT"

**Agent 会自动**:
1. 解析用户意图
2. 提取关键词、文件类型、时间范围
3. 调用 `file_search` 工具
4. 返回格式化的搜索结果

---

## 🚀 下一步

- [ ] 创建前端搜索界面
- [ ] 在聊天界面中集成文件搜索结果渲染
- [ ] 添加文件预览功能
- [ ] 支持批量操作（复制、移动文件）
