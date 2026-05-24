# UI 简体中文本地化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Mealpad 前端所有可见文案改为简体中文，enum 值（食谱类型、餐次、购物分类）在 UI 层显示中文标签，API 与数据库保持英文不变。

**Architecture:** 新建 `frontend/src/locale/zh.ts`（文案常量 + label 函数）与 `format.ts`（日期标题格式化）。各页面/组件 import 使用，不引入 i18n 库。纯函数用 Vitest 单测；页面改动靠 `npm run build` + 手动走查。

**Tech Stack:** React 19, TypeScript, Vite, Vitest（新增，仅测 locale 纯函数）

**Spec:** `docs/superpowers/specs/2026-05-23-ui-chinese-design.md`

---

## File Map

| 文件 | 职责 |
|------|------|
| `frontend/src/locale/zh.ts` | 全部 UI 文案、`recipeTypeLabel` / `slotLabel` / `categoryLabel` |
| `frontend/src/locale/format.ts` | `formatDayHeader(date)` → `2026-05-12 · 周一` |
| `frontend/src/locale/zh.test.ts` | label 与 format 单测 |
| `frontend/src/pages/*.tsx` | 替换英文硬编码为 `zh` 导入 |
| `frontend/src/components/RecipePicker.tsx` | 同上 |
| `frontend/index.html` | `lang="zh-CN"`、中文 title |
| `frontend/vite.config.ts` | PWA manifest 中文 |
| `frontend/package.json` | 添加 vitest script |

---

### Task 1: Vitest 脚手架 + locale 纯函数

**Files:**
- Create: `frontend/src/locale/format.ts`
- Create: `frontend/src/locale/zh.ts`
- Create: `frontend/src/locale/zh.test.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`（添加 vitest test config）

- [ ] **Step 1: 添加 vitest 依赖与 script**

Modify `frontend/package.json` scripts and devDependencies:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "test": "vitest run"
},
"devDependencies": {
  ...
  "vitest": "^3.0.0"
}
```

Run: `cd frontend && npm install`

- [ ] **Step 2: 写失败测试**

Create `frontend/src/locale/zh.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { formatDayHeader } from "./format";
import { categoryLabel, recipeTypeLabel, slotLabel } from "./zh";

describe("recipeTypeLabel", () => {
  it("maps known types", () => {
    expect(recipeTypeLabel("soup")).toBe("汤");
    expect(recipeTypeLabel("meat")).toBe("荤菜");
  });
  it("falls back to raw value", () => {
    expect(recipeTypeLabel("unknown")).toBe("unknown");
  });
});

describe("slotLabel", () => {
  it("maps lunch and dinner", () => {
    expect(slotLabel("lunch")).toBe("午餐");
    expect(slotLabel("dinner")).toBe("晚餐");
  });
});

describe("categoryLabel", () => {
  it("maps produce and pantry", () => {
    expect(categoryLabel("produce")).toBe("蔬果");
    expect(categoryLabel("pantry")).toBe("干货调料");
  });
});

describe("formatDayHeader", () => {
  it("formats ISO date with Chinese weekday", () => {
    // 2026-05-18 is Monday in local noon
    const d = new Date("2026-05-18T12:00:00");
    expect(formatDayHeader(d)).toBe("2026-05-18 · 周一");
  });
});
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd frontend && npm test`
Expected: FAIL — modules not found

- [ ] **Step 4: 实现 locale 模块**

Create `frontend/src/locale/format.ts`:

```typescript
const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"] as const;

export function formatDayHeader(date: Date): string {
  const iso = date.toISOString().slice(0, 10);
  return `${iso} · ${WEEKDAYS[date.getDay()]}`;
}
```

Create `frontend/src/locale/zh.ts`:

```typescript
export const zh = {
  loading: "加载中…",
  save: "保存",
  cancel: "取消",
  close: "关闭",
  delete: "删除",
  back: "返回",
  error: {
    loadFailed: "加载失败",
    saveFailed: "保存失败",
    deleteFailed: "删除失败",
    generic: "操作失败，请重试",
  },
  recipes: {
    title: "食谱",
    new: "+ 新建食谱",
    allTypes: "全部类型",
    mealPlan: "膳食计划",
    empty: "还没有食谱，来添加第一个吧。",
    ingredientsCount: (n: number) => `${n} 项食材`,
    deleteConfirm: (name: string) => `确定删除「${name}」？`,
    filterByType: "按类型筛选",
  },
  recipeForm: {
    newTitle: "新建食谱",
    editTitle: "编辑食谱",
    name: "名称",
    type: "类型",
    description: "描述",
    ingredients: "食材（每行一项）",
  },
  mealPlan: {
    title: "膳食计划",
    recipes: "食谱",
    generateList: "生成购物清单",
    viewList: "查看购物清单",
    autoFill: "AI 自动填充空槽",
    filling: "填充中…",
    addSlot: "+ 添加",
    loadFailed: "加载膳食计划失败",
    aiFillFailed: "AI 填充失败",
    generateListFailed: "生成购物清单失败",
  },
  picker: {
    title: "选择食谱",
    search: "搜索食谱…",
    clearSlot: "清空此餐",
  },
  shopping: {
    title: "购物清单",
    backToPlan: "返回膳食计划",
    empty: "还没有购物清单",
    regenerateConfirm: "重新生成清单？所有勾选状态将重置。",
    regenerateFailed: "重新生成失败",
    regenerating: "重新生成中…",
    regenerate: "重新生成清单",
  },
} as const;

const RECIPE_TYPE_LABELS: Record<string, string> = {
  soup: "汤",
  meat: "荤菜",
  veg: "素菜",
  noodle: "面食",
  rice: "米饭",
  salad: "沙拉",
  other: "其他",
};

const SLOT_LABELS: Record<string, string> = {
  lunch: "午餐",
  dinner: "晚餐",
};

const CATEGORY_LABELS: Record<string, string> = {
  produce: "蔬果",
  meat: "肉类",
  dairy: "乳制品",
  bakery: "烘焙",
  frozen: "冷冻",
  pantry: "干货调料",
  other: "其他",
};

export function recipeTypeLabel(type: string): string {
  return RECIPE_TYPE_LABELS[type] ?? type;
}

export function slotLabel(slot: string): string {
  return SLOT_LABELS[slot] ?? slot;
}

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}
```

Add to `frontend/vite.config.ts` inside `defineConfig`:

```typescript
/// <reference types="vitest/config" />
// at top of file if needed

export default defineConfig({
  ...
  test: {
    environment: "node",
  },
});
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npm test`
Expected: 5 tests PASS

- [ ] **Step 6: Commit 并 push**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/locale/
git commit -m "feat: add Chinese locale module with vitest"
git push origin main
```

---

### Task 2: 食谱页与表单中文化

**Files:**
- Modify: `frontend/src/pages/RecipesPage.tsx`
- Modify: `frontend/src/pages/RecipeFormPage.tsx`

- [ ] **Step 1: 更新 RecipesPage**

Replace English strings with imports:

```typescript
import { recipeTypeLabel, zh } from "../locale/zh";
```

Key replacements:
- `"Recipes"` → `zh.recipes.title`
- `"+ New recipe"` → `zh.recipes.new`
- `"All types"` → `zh.recipes.allTypes`
- `"Meal plan"` → `zh.recipes.mealPlan`
- `"Loading…"` → `zh.loading`
- `"No recipes yet..."` → `zh.recipes.empty`
- `` `${recipe.ingredients.length} ingredients` `` → `zh.recipes.ingredientsCount(recipe.ingredients.length)`
- `` `Delete "${recipe.name}"?` `` → `zh.recipes.deleteConfirm(recipe.name)`
- Section heading `{type}` → `{recipeTypeLabel(type)}`
- Error fallbacks → `zh.error.loadFailed` / `zh.error.deleteFailed`
- `aria-label="Filter by type"` → `zh.recipes.filterByType`
- Delete button text → `zh.delete`

- [ ] **Step 2: 更新 RecipeFormPage**

```typescript
import { zh } from "../locale/zh";
import { RECIPE_TYPES } from "../api";
import { recipeTypeLabel } from "../locale/zh";
```

Key replacements:
- Title: `isEdit ? zh.recipeForm.editTitle : zh.recipeForm.newTitle`
- Labels: `zh.recipeForm.name`, `.type`, `.description`, `.ingredients`
- Buttons: `zh.cancel`, `zh.save`
- Loading/error: `zh.loading`, `zh.error.loadFailed`, `zh.error.saveFailed`
- `<option>` text: `{recipeTypeLabel(t)}` instead of `{t}`

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: exit 0, no TypeScript errors

- [ ] **Step 4: Commit 并 push**

```bash
git add frontend/src/pages/RecipesPage.tsx frontend/src/pages/RecipeFormPage.tsx
git commit -m "feat: localize recipe pages to Simplified Chinese"
git push origin main
```

---

### Task 3: 膳食计划页中文化

**Files:**
- Modify: `frontend/src/pages/MealPlanPage.tsx`
- Modify: `frontend/src/components/RecipePicker.tsx`

- [ ] **Step 1: 更新 MealPlanPage**

Remove `DAY_NAMES` constant. Import:

```typescript
import { formatDayHeader } from "../locale/format";
import { slotLabel, zh } from "../locale/zh";
```

Key replacements:
- All UI strings → `zh.mealPlan.*`
- Day card title: replace `` `${DAY_NAMES[index]} ${iso}` `` with `{formatDayHeader(day)}`
- Slot label: `{slotLabel(slot)}` instead of `{slot}`
- Error handling: log `e` to console, show `zh.mealPlan.loadFailed` etc.

- [ ] **Step 2: 更新 RecipePicker**

```typescript
import { recipeTypeLabel, zh } from "../locale/zh";
```

Replace: title, search placeholder, clear button, close, error fallback.
Recipe row sub-label: `{recipeTypeLabel(recipe.type)}`

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: exit 0

- [ ] **Step 4: Commit 并 push**

```bash
git add frontend/src/pages/MealPlanPage.tsx frontend/src/components/RecipePicker.tsx
git commit -m "feat: localize meal plan and recipe picker to Chinese"
git push origin main
```

---

### Task 4: 购物清单页中文化

**Files:**
- Modify: `frontend/src/pages/ShoppingListPage.tsx`

- [ ] **Step 1: 更新 ShoppingListPage**

```typescript
import { categoryLabel, zh } from "../locale/zh";
```

Key replacements:
- All UI strings → `zh.shopping.*`
- Category section heading: `{categoryLabel(category)}` instead of `{category}`
- Keep `CATEGORY_ORDER` keys as English API values; only display layer translates
- `confirm()` → `zh.shopping.regenerateConfirm`

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: exit 0

- [ ] **Step 3: Commit 并 push**

```bash
git add frontend/src/pages/ShoppingListPage.tsx
git commit -m "feat: localize shopping list page to Chinese"
git push origin main
```

---

### Task 5: PWA manifest 与 HTML

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: 更新 index.html**

```html
<html lang="zh-CN">
...
<title>Mealpad · 家庭膳食计划</title>
```

- [ ] **Step 2: 更新 vite PWA manifest**

```typescript
manifest: {
  name: "Mealpad · 家庭膳食计划",
  short_name: "Mealpad",
  description: "家庭食谱、膳食计划与购物清单",
  ...
}
```

- [ ] **Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: exit 0; inspect `frontend/dist/manifest.webmanifest` for Chinese name/description

- [ ] **Step 4: Commit 并 push**

```bash
git add frontend/index.html frontend/vite.config.ts
git commit -m "feat: Chinese PWA manifest and html lang"
git push origin main
```

---

### Task 6: 端到端走查

**Files:** none

- [ ] **Step 1: 启动 dev 服务**

```bash
make dev-backend   # terminal 1
make dev-frontend  # terminal 2
```

- [ ] **Step 2: 浏览器走查（375×667）**

Checklist:
- [ ] `/recipes` — 标题、按钮、类型标签为中文
- [ ] 新建/编辑食谱 — 表单标签中文，类型下拉显示中文
- [ ] `/plan` — 日期行 `YYYY-MM-DD · 周X`，餐次「午餐/晚餐」
- [ ] 选食谱弹窗 — 中文标题与搜索框
- [ ] 购物清单 — 分类标题中文，勾选正常
- [ ] 删除确认框 — 中文

- [ ] **Step 3: 更新 spec 状态**

Modify `docs/superpowers/specs/2026-05-23-ui-chinese-design.md` line 4:
`状态：已完成`

```bash
git add docs/superpowers/specs/2026-05-23-ui-chinese-design.md
git commit -m "docs: mark UI Chinese localization spec as complete"
git push origin main
```

---

## Spec Coverage Checklist

| Spec 要求 | Task |
|-----------|------|
| locale/zh.ts 集中文案 | Task 1 |
| formatDayHeader | Task 1 |
| enum label 函数 | Task 1 |
| RecipesPage 文案 | Task 2 |
| RecipeFormPage 文案 | Task 2 |
| MealPlanPage + 日期格式 | Task 3 |
| RecipePicker 文案 | Task 3 |
| ShoppingListPage + 分类 | Task 4 |
| index.html lang/title | Task 5 |
| PWA manifest 中文 | Task 5 |
| 错误 fallback 中文 | Task 2–4 |
| 手动 E2E 验证 | Task 6 |

## Out of Scope (do not implement)

- react-i18next 或语言切换
- 后端改动
- 用户内容翻译
