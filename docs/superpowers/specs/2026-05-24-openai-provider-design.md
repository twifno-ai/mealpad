# 双 AI Provider（Claude + ChatGPT）— 设计说明

**日期：** 2026-05-24  
**状态：** 已批准，待实现  

## 目标

在保留 Anthropic Claude 的前提下，增加 OpenAI（ChatGPT API）作为可选 AI provider，用于**膳食计划填槽**与**购物清单合并**。Provider 仅通过 `backend/.env` 配置，无前端 UI。

## 已确认决策

| 项 | 选择 |
|---|---|
| 范围 | 膳食计划 + 购物清单，共用同一 provider |
| 配置 | 仅 `.env`，改后重启服务 |
| 缺 key | 服务正常启动；调用 AI 时返回明确中文错误 |
| 未设 `AI_PROVIDER` | 自动检测：有 `ANTHROPIC_API_KEY` 优先 Claude，否则 OpenAI |
| 显式 `AI_PROVIDER` 但 key 缺失 | 不 fallback，调用时报错 |
| OpenAI 默认模型 | `gpt-5.5` |
| Claude 默认模型 | `claude-sonnet-4-6`（可通过 env 覆盖） |

## 架构

```
backend/app/services/
├── ai.py                 # 对外入口：generate_plan, merge_ingredients
├── llm_config.py         # resolve_provider(), provider 枚举, key 校验
└── providers/
    ├── base.py           # Tool schema、system prompt、Protocol
    ├── anthropic.py      # Anthropic SDK（现有逻辑）
    └── openai_provider.py # openai SDK，Chat Completions + tools
```

`ai.py` 调用 `resolve_provider()` 选择实现；**tool 定义与 system prompt 集中在 `base.py`**，两 provider 输出形状一致。

## 环境变量

```bash
# 可选：anthropic | openai；留空则自动检测（Anthropic 优先）
AI_PROVIDER=

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.5
```

### Provider 解析

1. `AI_PROVIDER=anthropic` → Anthropic；无 key → 调用失败（中文错误）
2. `AI_PROVIDER=openai` → OpenAI；无 key → 调用失败（中文错误）
3. `AI_PROVIDER` 未设置或为空：
   - 有 `ANTHROPIC_API_KEY` → Anthropic
   - 否则有 `OPENAI_API_KEY` → OpenAI
   - 否则 → 调用失败（中文错误）
4. 显式 provider 不因缺 key 而 fallback 到另一厂商

## Anthropic 实现

- 保持现有 `anthropic` SDK + tool use + prompt caching
- 默认模型 `claude-sonnet-4-6`，由 `ANTHROPIC_MODEL` 覆盖
- 逻辑从 `ai.py` 迁入 `providers/anthropic.py`

## OpenAI 实现

- 依赖：官方 `openai` Python SDK
- API：Chat Completions（`client.chat.completions.create`）
- 默认模型：`gpt-5.5`（`OPENAI_MODEL` 可覆盖，如 `gpt-5.4-mini`）
- Tool calling：
  - 膳食计划：tool `assign_meals`，`tool_choice` 强制调用
  - 购物清单：tool `build_shopping_list`，`tool_choice` 强制调用
- 解析 `message.tool_calls[0].function.arguments` JSON
- System / user prompt 与 Claude 路径语义一致

## 对外行为（不变）

- `POST /api/meal-plan/generate`、`POST /api/shopping-lists` 请求/响应 JSON 不变
- 仍只填空槽；仍校验 AI 输出后再写库
- 前端无 provider 相关改动（错误信息已由 `httpErrors` 展示中文）

## 错误处理

新增 `AIServiceError`（或等价异常），路由层转为 HTTP 502/503，`detail` 为中文：

| 场景 | 消息示例 |
|------|----------|
| 未配置任何 key | 未配置 AI 服务：请在 backend/.env 中设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY |
| 指定 OpenAI 但无 key | 未配置 OpenAI API Key，请在 backend/.env 中设置 OPENAI_API_KEY |
| 指定 Anthropic 但无 key | 未配置 Anthropic API Key，请在 backend/.env 中设置 ANTHROPIC_API_KEY |
| SDK 调用失败 | OpenAI API 调用失败：{截断后的原因} |

## 依赖

- `backend/pyproject.toml` 增加 `openai>=1.0.0`
- `backend/.env.example` 增加上述变量说明

## 测试

| 测试文件 | 内容 |
|----------|------|
| `tests/test_llm_config.py` | provider 解析、自动检测、缺 key |
| `tests/test_ai_generate.py` | 现有 mock 改为 mock provider 层；增加 openai 分支 |
| `tests/test_shopping_lists.py` | 同上 |

不发起真实 API 调用。

## 文档

- 更新 `README.md`：OpenAI 配置示例
- 更新 `CLAUDE.md`：AI provider 约定

## 不在范围

- 前端 provider 选择 UI
- 计划与清单使用不同 provider
- Azure OpenAI、本地 Ollama 等
- Prompt caching（OpenAI 路径暂不实现 Anthropic 同款 cache_control）
