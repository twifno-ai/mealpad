# 双 AI Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development to implement task-by-task.

**Goal:** 支持 Claude 与 OpenAI（gpt-5.5）双 provider，通过 `.env` 选择；膳食计划与购物清单合并均走同一 provider。

**Architecture:** `llm_config.resolve_provider()` + `providers/anthropic.py` / `providers/openai_provider.py`；共享 tool schema 于 `providers/base.py`。`ai.py` 仅做委托。

**Spec:** `docs/superpowers/specs/2026-05-24-openai-provider-design.md`

---

### Task 1: LLM 配置与 provider 解析

**Files:**
- Create: `backend/app/services/llm_config.py`
- Create: `backend/tests/test_llm_config.py`
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: 写失败测试**

```python
# test_llm_config.py — 使用 monkeypatch settings
def test_auto_detect_prefers_anthropic(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant")
    monkeypatch.setattr(settings, "openai_api_key", "sk-openai")
    assert resolve_provider() == "anthropic"

def test_explicit_openai_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(AIServiceError, match="OPENAI"):
        ensure_provider_ready("openai")
```

- [ ] **Step 2: 实现 `llm_config.py` + 扩展 `config.py`**

```python
# config.py 新增
ai_provider: str = ""  # anthropic | openai | ""
anthropic_model: str = "claude-sonnet-4-6"
openai_api_key: str = ""
openai_model: str = "gpt-5.5"
```

- [ ] **Step 3: `pytest tests/test_llm_config.py -v` 全绿**

- [ ] **Step 4: Commit + push**

---

### Task 2: Provider 基类与 Anthropic 迁移

**Files:**
- Create: `backend/app/services/providers/__init__.py`
- Create: `backend/app/services/providers/base.py`
- Create: `backend/app/services/providers/anthropic.py`
- Modify: `backend/app/services/ai.py`（变薄，委托 anthropic）
- Modify: `backend/tests/test_ai_generate.py`（mock 路径更新）

- [ ] **Step 1: 将 ASSIGN_TOOL、MERGE_TOOL、system prompts 移入 `base.py`**

- [ ] **Step 2: `anthropic.py` 实现 `generate_plan` / `merge_ingredients`（从现有 ai.py 剪切）**

- [ ] **Step 3: `ai.py` 调用 `resolve_provider()` → anthropic 模块**

- [ ] **Step 4: 现有 AI 测试全绿 `pytest -v`**

- [ ] **Step 5: Commit + push**

---

### Task 3: OpenAI provider

**Files:**
- Create: `backend/app/services/providers/openai_provider.py`
- Modify: `backend/pyproject.toml`（`openai` 依赖）
- Create: `backend/tests/test_openai_provider.py`
- Modify: `backend/app/services/ai.py`

- [ ] **Step 1: 写 mock OpenAI client 的失败测试**

```python
def test_openai_generate_plan_parses_tool_call(monkeypatch):
    mock_response = FakeCompletion(tool_name="assign_meals", arguments={"assignments": [...]})
    monkeypatch.setattr(openai_provider, "_client", lambda: FakeOpenAI(mock_response))
    result = openai_provider.generate_plan(empty_slots, recipes)
    assert len(result) == 1
```

- [ ] **Step 2: 实现 `openai_provider.py`**

使用 `client.chat.completions.create(model=settings.openai_model, tools=[...], tool_choice=...)`

- [ ] **Step 3: `ai.py` 在 provider==openai 时委托 openai_provider**

- [ ] **Step 4: 测试全绿**

- [ ] **Step 5: Commit + push**

---

### Task 4: 路由层中文错误

**Files:**
- Modify: `backend/app/routers/meal_plan.py`
- Modify: `backend/app/routers/shopping_lists.py`
- Create or extend tests for AIServiceError → 502

- [ ] **Step 1: `generate` / `generate_shopping_list` catch `AIServiceError`，`HTTPException(502, detail=str(e))`**

- [ ] **Step 2: 测试缺 key 时返回 502 + 中文 detail**

- [ ] **Step 3: Commit + push**

---

### Task 5: 文档与 .env.example

**Files:**
- Modify: `backend/.env.example`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-05-24-openai-provider-design.md` 状态 → 已完成

- [ ] **Step 1: 文档补充 OpenAI 配置示例**

- [ ] **Step 2: Commit + push**

---

## 验证清单

- [ ] `AI_PROVIDER=openai` + 有效 `OPENAI_API_KEY` → 膳食计划 Auto-fill 成功
- [ ] 仅 `ANTHROPIC_API_KEY`、无 `AI_PROVIDER` → 仍走 Claude
- [ ] `AI_PROVIDER=openai` 无 key → 502 中文错误
- [ ] `pytest` 全绿
