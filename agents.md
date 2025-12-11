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

**核心功能：**

1. **响应清洗** - 实时过滤流式响应中的 `<think>` 块，确保 Droid CLI 收到纯净的输出
2. **思考可视化** - 被过滤的思考过程在代理控制台彩色显示，便于调试
3. **请求增强** - 可注入推理参数激活模型思维链能力
4. **多 API 格式适配** - 支持 OpenAI、Anthropic、Gemini、Azure OpenAI 等多种 API 格式转换
5. **LLM 参数管理** - 支持通过环境变量设置默认参数，请求参数优先级更高
6. **前端配置界面** - 提供 React 前端用于可视化配置和聊天测试

## 快速开始

```bash
# 安装后端依赖
pip install -r requirements.txt

# 配置环境变量
set UPSTREAM_API_KEY=your-api-key-here
set UPSTREAM_BASE_URL=https://api.deepseek.com

# 启动代理
python proxy.py

# (可选) 启动前端开发服务器
cd frontend
npm install
npm run dev
```

## Droid CLI 配置

在 Droid CLI 中使用代理：

```bash
# 设置 API 地址指向本地代理
droid config set api.baseUrl http://localhost:5000
```

## 环境变量

### 基础配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `UPSTREAM_API_KEY` | 上游服务 API 密钥 | - |
| `UPSTREAM_BASE_URL` | 上游服务地址 | `https://api.deepseek.com` |
| `PROXY_PORT` | 代理监听端口 | `5000` |
| `PROXY_API_KEY` | 本地代理服务的 API Key（可选，留空则不验证） | - |

### 默认 LLM 参数

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
| `FILTER_THINKING_TAGS` | 是否过滤 `<think>` 标签 | `true`/`false` |

## API 端点

### 核心端点

- `POST /v1/chat/completions` - 聊天补全（兼容 OpenAI 格式，支持流式）
- `GET /v1/models` - 模型列表
- `GET /health` - 健康检查

### 配置管理端点

- `GET /v1/config/reasoning` - 获取当前推理配置
- `GET /v1/config/reasoning/types` - 获取支持的推理类型和强度选项
- `GET /v1/config/proxy` - 获取代理配置
- `PUT /v1/config/proxy` - 更新代理配置

## 支持的 API 格式

| 格式 | 说明 |
|------|------|
| `openai` | OpenAI 兼容 API（默认） |
| `openai-response` | OpenAI Response API |
| `anthropic` | Anthropic Claude API |
| `gemini` | Google Gemini API |
| `azure-openai` | Azure OpenAI Service |

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
