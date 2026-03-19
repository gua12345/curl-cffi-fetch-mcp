# curl-cffi Fetch MCP

一个基于 curl-cffi 的网页抓取服务，同时提供 MCP (Model Context Protocol) 和 OneAPI 兼容的 REST API 接口。

## 核心特性

- **双协议支持**：MCP Streamable HTTP + OneAPI REST API
- **浏览器指纹模拟**：使用 curl-cffi 的 `impersonate` 特性绕过反爬虫检测
- **HTML 转 Markdown**：自动将网页内容转换为 Markdown 格式
- **灵活配置**：三层配置优先级（代码默认 < .env < 请求参数）
- **代理池管理**：支持为不同网站配置专用代理
- **统一鉴权**：两个端点共享鉴权逻辑

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少需要设置 `API_KEY`：

```env
API_KEY=your-secret-api-key-here
```

### 3. 运行服务

```bash
# 开发模式
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 或直接运行
python src/main.py
```

### 4. 访问文档

服务启动后，访问：
- API 文档：http://localhost:8000/docs
- 服务信息：http://localhost:8000/

## API 使用

### OneAPI 接口

OneAPI 提供标准的 REST API 接口，所有接口都需要通过 API Key 鉴权。

#### 1. 查询支持的浏览器指纹

获取所有 curl-cffi 支持的浏览器指纹列表（动态从库中提取）。

```bash
curl -X GET "http://localhost:8000/v1/impersonates" \
  -H "Authorization: Bearer your-api-key"
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": "chrome136",
      "name": "Chrome 136",
      "description": "Chrome 136 版本浏览器指纹"
    },
    {
      "id": "safari184",
      "name": "Safari 18.4",
      "description": "Safari 18.4 版本浏览器指纹"
    }
  ],
  "error": null
}
```

#### 2. 查询可用代理

获取配置的代理池列表。

```bash
curl -X GET "http://localhost:8000/v1/proxies" \
  -H "Authorization: Bearer your-api-key"
```

**响应示例**：
```json
{
  "success": true,
  "data": [
    {
      "id": "hk",
      "description": "香港代理"
    }
  ],
  "error": null
}
```

#### 3. 抓取网页

使用浏览器指纹模拟抓取网页并转换为 Markdown。

```bash
curl -X POST "http://localhost:8000/v1/fetch" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "impersonate": "chrome136",
    "proxy": "hk",
    "timeout": 30
  }'
```

**请求参数**：
- `url` (必填): 目标网页 URL
- `impersonate` (可选): 浏览器指纹类型，默认 `chrome`
- `proxy` (可选): 代理标识符
- `headers` (可选): 自定义请求头
- `cookies` (可选): 自定义 Cookies
- `timeout` (可选): 超时时间（秒），默认 30

**响应示例**：
```json
{
  "success": true,
  "data": {
    "url": "https://example.com",
    "status_code": 200,
    "content_type": "text/html",
    "markdown": "# Example Domain\n\nThis domain is for use in...",
    "length": 1256
  },
  "error": null
}
```

### MCP 接口

MCP (Model Context Protocol) 提供标准的 JSON-RPC 2.0 接口，供 AI 客户端调用。

#### 1. 初始化连接

```bash
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

#### 2. 列出可用工具

```bash
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }'
```

**可用工具**：
- `list_proxies`: 查询可用的代理列表
- `fetch_url_tool`: 使用浏览器指纹模拟抓取网页并转换为 Markdown

#### 3. 调用 list_proxies 工具

```bash
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "list_proxies",
      "arguments": {}
    }
  }'
```

#### 4. 调用 fetch_url_tool 工具

```bash
curl -X POST "http://localhost:8000/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "fetch_url_tool",
      "arguments": {
        "url": "https://example.com",
        "impersonate": "chrome136",
        "proxy": "hk",
        "timeout": 30
      }
    }
  }'
```

**工具参数**：
- `url` (必填): 目标网页 URL
- `impersonate` (可选): 浏览器指纹类型，默认 `chrome`
- `proxy` (可选): 代理标识符
- `headers` (可选): 自定义请求头
- `cookies` (可选): 自定义 Cookies
- `timeout` (可选): 超时时间（秒），默认 30

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HOST` | 服务监听地址 | `0.0.0.0` |
| `PORT` | 服务监听端口 | `8000` |
| `DEBUG` | 调试模式 | `false` |
| `API_KEY` | API 鉴权密钥（必填） | - |
| `DEFAULT_IMPERSONATE` | 默认浏览器类型 | `chrome` |
| `DEFAULT_TIMEOUT` | 默认超时时间（秒） | `30` |
| `DEFAULT_PROXY` | 默认代理标识符 | - |
| `PROXY_POOL` | 代理池配置（JSON） | `{}` |
| `HTML2TEXT_BODY_WIDTH` | Markdown 文本宽度 | `0` |
| `HTML2TEXT_IGNORE_LINKS` | 忽略链接 | `false` |
| `HTML2TEXT_IGNORE_IMAGES` | 忽略图片 | `false` |

### 代理池配置

在 `.env` 中配置代理池（JSON 格式），支持 HTTP、HTTPS 和 SOCKS5 代理。

**基本代理配置**：
```env
PROXY_POOL={"hk": {"url": "http://127.0.0.1:17890", "description": "香港代理"}}
```

**带鉴权的代理配置**：
```env
# HTTP 代理带用户名密码
PROXY_POOL={"auth_proxy": {"url": "http://username:password@proxy.example.com:8080", "description": "带鉴权的 HTTP 代理"}}

# SOCKS5 代理带用户名密码
PROXY_POOL={"socks_proxy": {"url": "socks5://username:password@proxy.example.com:1080", "description": "带鉴权的 SOCKS5 代理"}}
```

**多代理配置**：
```env
PROXY_POOL={"hk": {"url": "http://hk-proxy:8080", "description": "香港代理"}, "sg": {"url": "http://user:pass@sg-proxy:8080", "description": "新加坡代理"}, "us": {"url": "socks5://us-proxy:1080", "description": "美国代理"}}
```

### 浏览器指纹配置

curl-cffi 支持 37+ 种浏览器指纹，包括：

**推荐使用**（最新版本）：
- `chrome136` - Chrome 136（推荐）
- `safari184` - Safari 18.4（推荐）
- `safari184_ios` - Safari 18.4 iOS（推荐）
- `firefox135` - Firefox 135

**通用别名**（自动使用最新版本）：
- `chrome` - 自动使用最新 Chrome
- `safari` - 自动使用最新 Safari
- `safari_ios` - 自动使用最新 Safari iOS
- `firefox` - 自动使用最新 Firefox

**完整列表**：
通过 `GET /v1/impersonates` 接口查询所有支持的浏览器指纹。

## 项目结构

```
curl-cffi-fetch-mcp/
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用入口
│   ├── config.py                # 配置管理
│   ├── auth.py                  # 鉴权中间件
│   ├── core/
│   │   ├── __init__.py
│   │   ├── fetcher.py           # 核心抓取逻辑
│   │   ├── converter.py         # HTML → Markdown 转换
│   │   └── headers_generator.py # 浏览器指纹信息（动态获取）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── mcp_endpoint.py      # MCP 端点
│   │   └── oneapi_endpoint.py   # OneAPI 端点
│   └── models/
│       ├── __init__.py
│       ├── request.py           # 请求数据模型
│       └── response.py          # 响应数据模型
├── .env                         # 环境配置
├── .env.example                 # 配置示例
├── requirements.txt             # Python 依赖
└── README.md                    # 项目文档
```

## 技术栈

- **FastAPI 0.135.1**：高性能异步 Web 框架
- **curl-cffi 0.14.0**：支持浏览器指纹模拟的 HTTP 客户端（37+ 种浏览器指纹）
- **html2text 2025.4.15**：HTML 到 Markdown 转换
- **pydantic 2.12.5**：数据验证和序列化
- **pydantic-settings 2.13.1**：类型安全的配置管理
- **mcp 1.26.0**：MCP 协议 Python SDK
- **uvicorn 0.42.0**：ASGI 服务器

## 安全考虑

- API Key 必须通过 HTTPS 传输（生产环境）
- 支持 Header 和 Query 两种鉴权方式
- URL 格式验证，防止 SSRF 攻击
- 限制可访问的协议（仅 http/https）

## 生产部署

### 使用 uvicorn

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 使用 gunicorn + uvicorn worker

```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 许可证

MIT License
