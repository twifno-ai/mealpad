# Mealpad — v3 PWA Mobile Shell Plan

## Context

v2 已交付：饮食记录、实拍、食谱封面、Journal 页。当前手机使用方式为 Safari 打开局域网地址或「添加到主屏幕」，**无底部 Tab、无统一连接失败 UI**。

v3 在 **零 Apple 开发者账号、不改后端 API** 前提下，强化 PWA 为家庭 iPhone 上的「App 级」体验（用户原意向 Capacitor iOS，评估账号成本后改为 **R3 强化 PWA**）。

**设计 spec：** [superpowers/specs/2026-05-23-pwa-mobile-shell-design.md](superpowers/specs/2026-05-23-pwa-mobile-shell-design.md)

## v3 锁定决策

| 区域 | 选择 |
|---|---|
| 形态 | PWA only（无 Capacitor） |
| 优先级 | G1 连接引导 + G2 App 壳 |
| Tab | 计划 / 食谱 / 记录 / 购物清单 |
| 服务器 | health 检测 + 中文引导；**不可**应用内改 IP |
| 架构 | `AppShell` layout + `ConnectionProvider` |
| 购物清单 | 独立路由 `/shopping/:weekStart`，默认本周 |
| 设置 | `/settings`，从计划页 ⚙ 进入 |

## 架构增量

```
frontend/src/
├── context/
│   └── ConnectionContext.tsx
├── components/
│   ├── AppShell.tsx
│   ├── TabBar.tsx
│   ├── ConnectionScreen.tsx
│   └── OfflineBanner.tsx
├── pages/
│   ├── SettingsPage.tsx          # 新
│   ├── MealPlanPage.tsx          # 减重复 nav
│   ├── JournalPage.tsx           # 减返回 plan
│   ├── ShoppingListPage.tsx      # 独立 Tab 空状态
│   └── RecipesPage.tsx           # 减重复 link
├── App.tsx                       # 嵌套路由
├── locale/zh.ts
└── styles.css
```

**后端：** 无变更。

---

## Milestones

每里程碑结束 **commit + push**（`twifno-ai <twifnoai@gmail.com>`）。

---

### V3-M1 — 连接状态与设置页

**Files:**

- Create: `frontend/src/context/ConnectionContext.tsx`
- Create: `frontend/src/components/ConnectionScreen.tsx`
- Create: `frontend/src/components/OfflineBanner.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/locale/zh.ts`
- Modify: `frontend/src/main.tsx` or `App.tsx`（包裹 Provider）

**行为：**

- mount 时 `GET /api/health`（3s timeout）
- 失败 → `ConnectionScreen`；成功 → children
- `online`/`offline` → `OfflineBanner`
- `SettingsPage`：origin、复制、手动检查、帮助文案

**Tests:**

- Vitest：`zh.connection.*`、`zh.settings.*` keys

**Verify:** 停服务器 → 刷新 → 见全屏错误；恢复 → 重试成功

**Commit:** `feat(v3): PWA connection health check and settings page`

---

### V3-M2 — AppShell 与四 Tab 路由

**Files:**

- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/TabBar.tsx`
- Modify: `frontend/src/App.tsx` — 嵌套 `AppShell` 路由
- Modify: `frontend/src/styles.css` — tab-bar、safe-area、shell padding
- Modify: `frontend/src/locale/zh.ts` — `tabs.*`

**路由：**

- Tab 内：`/plan/:weekStart`、`/recipes`、`/journal/:weekStart`、`/shopping/:weekStart`
- 表单：`/recipes/new`、`/recipes/:id/edit` 仍在 Shell 内
- `/settings` 在 Shell 内、无 Tab 高亮
- redirect：`/`、`/plan`、`/journal`、`/shopping` → 本周

**Verify:** 375×667 四 Tab 切换；当前 Tab 高亮；内容不被 Tab 遮挡

**Commit:** `feat(v3): bottom tab bar and app shell layout`

---

### V3-M3 — 页面精简与购物清单 Tab

**Files:**

- Modify: `frontend/src/pages/MealPlanPage.tsx` — ⚙ settings；去 journal/recipes header link
- Modify: `frontend/src/pages/JournalPage.tsx` — 去「返回计划」主链
- Modify: `frontend/src/pages/RecipesPage.tsx` — 去 plan link
- Modify: `frontend/src/pages/ShoppingListPage.tsx` — 空状态；弱返回；周导航保留
- Modify: `frontend/src/App.tsx` — `/plan/:week/shopping` → redirect `/shopping/:week`

**Verify:** 购物清单 Tab 打开默认本周；旧 shopping URL redirect；空清单引导去计划

**Commit:** `feat(v3): adapt pages for tab navigation and shopping route`

---

### V3-M4 — PWA manifest 与 iOS meta

**Files:**

- Modify: `frontend/vite.config.ts` — `start_url: "/"` 等
- Modify: `frontend/index.html` — `viewport-fit=cover`、apple meta
- Modify: `frontend/src/App.tsx` 或 Connection — 启动 loading 态

**Verify:** 重新 `make build`；主屏幕图标打开 standalone；状态栏/theme 正确

**Commit:** `feat(v3): polish PWA manifest and iOS standalone meta`

---

### V3-M5 — 文档与全量验证

**Files:**

- Modify: `docs/SPEC.md` — PWA App 壳能力
- Modify: `README.md` — 主屏幕安装步骤强调四 Tab；troubleshooting 链到 ConnectionScreen 逻辑
- Modify: `docs/superpowers/specs/2026-05-23-pwa-mobile-shell-design.md` — 状态 → 已完成

**Verify:**

```bash
cd frontend && npm test && npm run build
make build && make serve   # iPhone 主屏幕抽检
```

**Commit:** `docs: update SPEC and README for v3 PWA mobile shell`

---

## 全量回归

- [ ] v2 饮食记录 / 封面上传仍正常
- [ ] AI fill / regenerate / 购物清单生成正常
- [ ] 深链 `/recipes/1/edit` 可打开
- [ ] dev：`npm run dev` + proxy 仍可用

## Related docs

| Doc | Purpose |
|---|---|
| [2026-05-23-pwa-mobile-shell-design.md](superpowers/specs/2026-05-23-pwa-mobile-shell-design.md) | 设计细节 |
| [PLAN-v2.md](PLAN-v2.md) | 上一版本里程碑 |
