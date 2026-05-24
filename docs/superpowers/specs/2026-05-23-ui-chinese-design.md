# UI 简体中文本地化 — 设计说明

**日期：** 2026-05-23  
**状态：** 已批准，待实现  
**范围：** 方案 B — 界面中文 + enum 展示标签；API 保持英文

## 目标

将 Mealpad 前端所有用户可见文案改为**简体中文**，并对食谱类型、餐次、购物分类等 enum 值提供中文展示标签。数据库与 API 字段不变，不做完整 i18n 框架。

## 已确认决策

| 项 | 选择 |
|---|---|
| 范围 | 界面文案 + enum 展示标签；用户输入内容不翻译 |
| 书写 | 简体中文 |
| 日期格式 | ISO 日期 + 中文星期，如 `2026-05-12 · 周一` |
| 实现方式 | 集中式 `locale/zh.ts` 模块（方案 2） |
| URL / API | 仍使用 `YYYY-MM-DD` 与英文 enum 值 |

## 架构

```
frontend/src/locale/
├── zh.ts          # UI 文案常量 + enum → 中文标签映射
└── format.ts      # formatDayHeader(date) → "2026-05-12 · 周一"
```

页面与组件从 `locale/zh.ts` 导入文案与 `recipeTypeLabel()`、`slotLabel()`、`categoryLabel()` 等函数，不在 TSX 内散落硬编码中文（enum 映射除外仅在 zh.ts 一处维护）。

**不引入** `react-i18next` 或其他 i18n 库。

## Enum 展示映射

### 食谱类型（API `type` 字段）

| API 值 | 中文标签 |
|--------|----------|
| soup | 汤 |
| meat | 荤菜 |
| veg | 素菜 |
| noodle | 面食 |
| rice | 米饭 |
| salad | 沙拉 |
| other | 其他 |

### 餐次（API `slot` 字段）

| API 值 | 中文标签 |
|--------|----------|
| lunch | 午餐 |
| dinner | 晚餐 |

### 购物分类（API `category` 字段）

| API 值 | 中文标签 |
|--------|----------|
| produce | 蔬果 |
| meat | 肉类 |
| dairy | 乳制品 |
| bakery | 烘焙 |
| frozen | 冷冻 |
| pantry | 干货调料 |
| other | 其他 |

未知 enum 值：fallback 显示原始英文值。

## 日期与星期

- `formatDayHeader(date: Date)` → `"2026-05-12 · 周一"`
- ISO 部分：`date.toISOString().slice(0, 10)`（与现有 API 一致）
- 星期：`["周日","周一","周二","周三","周四","周五","周六"][date.getDay()]`
- 周导航范围行：`2026-05-12 – 2026-05-18`（保留 ISO，中间用 en dash）

## UI 文案清单

### 全局 / 通用

| 键 | 中文 |
|----|------|
| loading | 加载中… |
| save | 保存 |
| cancel | 取消 |
| close | 关闭 |
| delete | 删除 |
| back | 返回 |
| error.loadFailed | 加载失败 |
| error.saveFailed | 保存失败 |
| error.deleteFailed | 删除失败 |
| error.generic | 操作失败，请重试 |

### 食谱页 (`RecipesPage`)

| 英文（现） | 中文 |
|-----------|------|
| Recipes | 食谱 |
| + New recipe | + 新建食谱 |
| All types | 全部类型 |
| Meal plan | 膳食计划 |
| No recipes yet. Add your first one. | 还没有食谱，来添加第一个吧。 |
| N ingredients | {n} 项食材 |
| Delete "{name}"? | 确定删除「{name}」？ |
| Filter by type | 按类型筛选 |

### 食谱表单 (`RecipeFormPage`)

| 英文（现） | 中文 |
|-----------|------|
| New recipe | 新建食谱 |
| Edit recipe | 编辑食谱 |
| Name | 名称 |
| Type | 类型 |
| Description | 描述 |
| Ingredients (one per line) | 食材（每行一项） |
| Save | 保存 |

### 膳食计划 (`MealPlanPage`)

| 英文（现） | 中文 |
|-----------|------|
| Meal plan | 膳食计划 |
| Recipes | 食谱 |
| Generate shopping list | 生成购物清单 |
| View shopping list | 查看购物清单 |
| Auto-fill empty slots with AI | AI 自动填充空槽 |
| Filling… | 填充中… |
| + add | + 添加 |
| Failed to load plan | 加载膳食计划失败 |
| AI fill failed | AI 填充失败 |
| Failed to generate list | 生成购物清单失败 |

### 选食谱弹窗 (`RecipePicker`)

| 英文（现） | 中文 |
|-----------|------|
| Choose recipe | 选择食谱 |
| Search recipes… | 搜索食谱… |
| Clear slot | 清空此餐 |

### 购物清单 (`ShoppingListPage`)

| 英文（现） | 中文 |
|-----------|------|
| Shopping list | 购物清单 |
| Back to plan | 返回膳食计划 |
| No shopping list yet | 还没有购物清单 |
| Regenerate list? All check marks will reset. | 重新生成清单？所有勾选状态将重置。 |
| Regenerate failed | 重新生成失败 |
| Regenerating… | 重新生成中… |
| Regenerate list | 重新生成清单 |

## 错误处理

- 用户可见错误一律使用 `zh.ts` 中的中文 fallback。
- `catch` 中 API 返回的英文 body 写入 `console.error`，不直接展示。
- `confirm()` 对话框使用中文文案。

## PWA 与 HTML

**`index.html`：**
- `<html lang="zh-CN">`
- `<title>Mealpad · 家庭膳食计划</title>`

**`vite.config.ts` manifest：**
- `name`: `Mealpad · 家庭膳食计划`
- `short_name`: `Mealpad`
- `description`: `家庭食谱、膳食计划与购物清单`

## 不改动的部分

- 后端路由、模型、AI prompt、测试
- API 请求/响应 JSON 字段名与 enum 值
- 用户创建的食谱名、描述、食材文本
- AI 生成的购物清单 `item.text` 行内容
- 路由路径（`/recipes`、`/plan/:weekStart` 等）

## 涉及文件

| 操作 | 文件 |
|------|------|
| 新建 | `frontend/src/locale/zh.ts` |
| 新建 | `frontend/src/locale/format.ts` |
| 修改 | `frontend/src/pages/RecipesPage.tsx` |
| 修改 | `frontend/src/pages/RecipeFormPage.tsx` |
| 修改 | `frontend/src/pages/MealPlanPage.tsx` |
| 修改 | `frontend/src/pages/ShoppingListPage.tsx` |
| 修改 | `frontend/src/components/RecipePicker.tsx` |
| 修改 | `frontend/index.html` |
| 修改 | `frontend/vite.config.ts` |

## 验证

1. `make dev-frontend` + `make dev-backend`，浏览器走一遍：
   - 食谱 CRUD 文案为中文
   - 膳食计划显示 `2026-05-12 · 周一` 格式
   - 餐次、类型、分类显示中文标签
   - 确认框、错误提示为中文
2. 375×667 视口：按钮可点、无横向滚动
3. `make build` 成功；manifest 中文名称正确

## 后续（不在本次范围）

- 语言切换
- 后端错误码中文化
- 繁体中文
