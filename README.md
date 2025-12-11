# Droid BYOK Unleashed

一个用于 Droid CLI BYOK 模式的中间人代理服务，解决推理模型思维链内容导致的工具调用失败问题。

## 问题背景

在使用 Droid CLI 的 BYOK（自带密钥）模式连接推理模型（如 DeepSeek R1）时，模型返回的 `<think>...</think>` 标签会导致：

- 工具调用（Tool Use）解析失败
- JSON 格式错误
- 上下文 Token 浪费

## 解决方案

本代理服务作为 Droid CLI 和上游推理服务之间的中间层：

```
Droid CLI  <-->  Proxy (localhost:5000)  <-->  上游 API (DeepSeek/OpenAI/Anthropic/Gemini 等)
```

### 核心功能

1. **响应清洗** - 实时过滤流式响应中的 `<think>` 块，确保 Droid CLI 收到纯净的输出
2. **思考可视化** - 被过滤的思考过程在代理控制台彩色显示，便于调试
3. **请求增强** - 可注入推理参数激活模型思维链能力
4. **多 API 格式适配** - 支持 OpenAI、Anthropic、Gemini、Azure OpenAI 等多种 API 格式转换
5. **LLM 参数管理** - 支持通过环境变量设置默认参数，请求参数优先级更高
6. **前端配置界面** - 提供 React 前端用于可视化配置和聊天测试

## 快速开始

### 1. 安装后端依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并编辑：

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

或直接设置环境变量：

```bash
# Windows
set UPSTREAM_API_KEY=your-api-key-here
set UPSTREAM_BASE_URL=https://api.deepseek.com

# Linux/macOS
export UPSTREAM_API_KEY=your-api-key-here
export UPSTREAM_BASE_URL=https://api.deepseek.com
```

### 3. 启动代理服务

```bash
python proxy.py
```

### 4. (可选) 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，会自动连接到代理服务。

## Droid CLI 配置

在 Droid CLI 中使用代理：

```bash
droid config set api.baseUrl http://localhost:5000
```

## 环境变量配置

### 基础配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `UPSTREAM_API_KEY` | 上游服务 API 密钥 | - |
| `UPSTREAM_BASE_URL` | 上游服务地址 | `https://api.deepseek.com` |
| `PROXY_PORT` | 代理监听端口 | `5000` |
| `PROXY_API_KEY` | 本地代理服务的 API Key（可选，留空则不验证） | - |

### 默认 LLM 参数

这些参数在客户端未指定时使用，客户端请求参数优先级更高。

| 变量 | 说明 | 范围 |
|------|------|------|
| `DEFAULT_TEMPERATURE` | 控制随机性 | 0-2 |
| `DEFAULT_TOP_P` | 核采样阈值 | 0-1 |
| `DEFAULT_TOP_K` | Top-k 采样 | 1-100 |
| `DEFAULT_MAX_TOKENS` | 最大输出 Token 数 | 1-1000000 |
| `DEFAULT_PRESENCE_PENALTY` | 存在惩罚 | -2 到 2 |
| `DEFAULT_FREQUENCY_PENALTY` | 频率惩罚 | -2 到 2 |
| `DEFAULT_SEED` | 随机种子 | 整数 |

### 推理模型配置

| 变量 | 说明 | 可选值 |
|------|------|--------|
| `REASONING_ENABLED` | 是否启用推理模式 | `true`/`false` |
| `REASONING_TYPE` | 推理参数类型 | `deepseek`, `openai`, `anthropic`, `gemini`, `qwen`, `openrouter`, `custom` |
| `REASONING_EFFORT` | 推理强度 | `none`, `minimal`, `low`, `medium`, `high`, `auto` |
| `REASONING_BUDGET_TOKENS` | 思考 Token 预算 | 整数 |
| `REASONING_CUSTOM_PARAMS` | 自定义推理参数 (JSON) | JSON 字符串 |
| `FILTER_THINKING_TAGS` | 是否过滤 `<think>` 标签 | `true`/`false` (默认 `true`) |

## API 端点

### 核心端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/chat/completions` | POST | 聊天补全（兼容 OpenAI 格式，支持流式） |
| `/v1/models` | GET | 获取模型列表 |
| `/health` | GET | 健康检查 |

### 配置管理端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/config/reasoning` | GET | 获取当前推理配置 |
| `/v1/config/reasoning/types` | GET | 获取支持的推理类型和强度选项 |
| `/v1/config/proxy` | GET | 获取代理配置 |
| `/v1/config/proxy` | PUT | 更新代理配置 |

## 使用示例

### 基本聊天请求

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

### 带参数的请求

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Explain quantum computing"}],
    "stream": true,
    "temperature": 0.7,
    "max_tokens": 2048
  }'
```

### 使用自定义上游 API

通过请求头指定上游服务：

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -H "X-Upstream-Base-URL: https://api.openai.com" \
  -H "X-API-Format: openai" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 支持的 API 格式

| 格式 | 说明 | 适用服务 |
|------|------|----------|
| `openai` | OpenAI 兼容 API（默认） | OpenAI, DeepSeek, 兼容服务 |
| `openai-response` | OpenAI Response API | OpenAI Response API |
| `anthropic` | Anthropic Claude API | Claude 系列 |
| `gemini` | Google Gemini API | Gemini 系列 |
| `azure-openai` | Azure OpenAI Service | Azure 托管的 OpenAI |

## 支持的推理模型类型

| 类型 | 参数格式 | 适用模型 |
|------|----------|----------|
| `deepseek` | `thinking.type` | DeepSeek R1/V3.1 |
| `openai` | `reasoning_effort` | OpenAI o1/o3/GPT-5 |
| `anthropic` | `thinking.budget_tokens` | Claude 3.7/4 |
| `gemini` | `thinkingConfig` | Gemini 2.5+ |
| `qwen` | `enable_thinking` | Qwen3 |
| `openrouter` | `reasoning.enabled` | OpenRouter |
| `custom` | 自定义 JSON | 任意 |

## 项目结构

```
droid-byok-unleashed/
├── proxy.py              # 主代理服务
├── proxy_config.py       # 代理配置管理
├── proxy_config.json     # 持久化配置文件
├── reasoning_config.py   # 推理模型配置
├── reasoning_builder.py  # 推理参数构建器
├── api_format_adapter.py # API 格式适配器
├── requirements.txt      # Python 依赖
├── .env.example          # 环境变量示例
├── test_filter.py        # StreamFilter 单元测试
├── test_params.py        # LLM 参数处理单元测试
└── frontend/             # React 前端
    ├── src/
    │   ├── components/   # UI 组件
    │   ├── hooks/        # React Hooks
    │   ├── services/     # API 服务
    │   └── types/        # TypeScript 类型定义
    └── package.json
```

## 运行测试

```bash
# 运行 StreamFilter 测试
python test_filter.py

# 运行 LLM 参数处理测试
python test_params.py
```

## 技术栈

### 后端
- Python 3.8+
- Flask + Flask-CORS
- Requests

### 前端
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Lucide Icons

## 参考项目

- UI 设计参考: [oroio](https://github.com/notdp/oroio)
- LLM 配置设计参考: [cherry-studio](https://github.com/CherryHQ/cherry-studio)
