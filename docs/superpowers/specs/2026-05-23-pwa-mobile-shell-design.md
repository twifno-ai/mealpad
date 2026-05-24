# PWA 移动端 App 壳 — 设计说明

**日期：** 2026-05-23  
**状态：** 已确认，待实现  
**实现计划：** [PLAN-v3-pwa.md](../../PLAN-v3-pwa.md)

## 目标

在不使用 Capacitor / App Store、不改动后端 API 的前提下，把现有 React PWA 做成 **iPhone 主屏幕上的「像原生 App」体验**，重点：

1. **G1 连接与配置（C1）** — 启动 health 检测；失败时中文全屏引导；设置页展示/复制当前地址；**不支持**应用内改服务器 IP。
2. **G2 App 壳** — 底部四 Tab 导航、safe-area 适配、standalone 全屏、启动加载态。

## 背景与决策路径

| 阶段 | 选择 |
|---|---|
| 最初方向 | Capacitor 壳 App（B） |
| 平台 | 仅 iOS（P1） |
| 分发 | 用户询问免开发者账号 → 说明 iOS 限制 |
| 最终形态 | **强化 PWA（R3）**，零 Apple 开发者账号 |
| 优先级 | G1 + G2（不含离线 G3、拍照增强 G4） |
| Tab | 计划 / 食谱 / 记录 / 购物清单（T1） |
| 服务器 | C1：health + 引导，不改 API 域名 |

## 非目标

- Capacitor、TestFlight、App Store
- Service Worker 离线缓存（食谱/计划本地副本）
- 相机/压缩/upload 流程改造
- 可配置 `apiBase` + 后端 CORS
- 推送通知
- Android 专属原生能力（PWA 在 Android 上仍可用，但不单独优化）

## 架构

### 方案：Layout 路由 + 底部 TabBar（方案 1）

```
App
├── ConnectionProvider     # health 状态、重试、online/offline
├── ConnectionScreen       # health 失败全屏（挡住 Shell）
└── AppShell
    ├── Outlet             # 子路由页面
    └── TabBar             # 固定底部 4 Tab
```

**原则：** 现有页面组件（`MealPlanPage` 等）尽量复用；路由与壳层集中在新文件。

## 路由

| 路径 | 页面 | Tab |
|---|---|---|
| `/` | redirect → `/plan/{本周一}` | — |
| `/plan` | redirect → `/plan/{本周一}` | — |
| `/plan/:weekStart` | `MealPlanPage` | 膳食计划 |
| `/recipes` | `RecipesPage` | 食谱 |
| `/recipes/new`, `/recipes/:id/edit` | `RecipeFormPage` | （无 Tab 高亮，仍显示 Shell） |
| `/journal` | redirect → `/journal/{本周一}` | — |
| `/journal/:weekStart` | `JournalPage` | 饮食记录 |
| `/shopping` | redirect → `/shopping/{本周一}` | — |
| `/shopping/:weekStart` | `ShoppingListPage` | 购物清单 |
| `/settings` | `SettingsPage` | （非 Tab，从计划页 ⚙ 进入） |

**兼容：**

- 保留 `/plan/:weekStart/shopping` → **redirect** 到 `/shopping/:weekStart`（旧书签不失效）。

**Tab 与路由映射：**

- 计划 Tab 高亮：`/plan/*`
- 食谱 Tab：`/recipes`（不含 `/recipes/new`、`/recipes/:id/edit` 时可仍高亮食谱 Tab）
- 记录 Tab：`/journal/*`
- 清单 Tab：`/shopping/*`

## G1：连接体验

### Health 检查

- 时机：App 首次 mount；用户点「重试」；从 `SettingsPage` 手动检查。
- 请求：`GET /api/health`，**3 秒**超时（`AbortController`）。
- 成功：`{ ok: true }` → 进入/保持 Shell。
- 失败：显示 `ConnectionScreen`，阻止 Tab 内容交互。

### ConnectionScreen（全屏）

中文文案要点：

- 标题：「无法连接 Mealpad 服务器」
- 说明：请确认手机与运行 Mealpad 的电脑在 **同一 Wi‑Fi**
- 检查项：`make serve` 是否在运行；Mac IP 是否变化（变化需 Safari 打开新地址并重新「添加到主屏幕」）
- 按钮：**重试** | **复制当前地址**（`window.location.origin`）| **连接帮助**（展开页内短说明，不外链必填）

### 离线条

- `window` `online` / `offline` 事件
- 离线时 Shell 顶部固定细条：「当前无网络」——不替代 health 失败屏（服务器可达但无网时 health 也会失败）

### SettingsPage

入口：膳食计划页 header **⚙**（非 Tab）。

内容：

- 当前服务器地址（`window.location.origin`）+ 复制
- 「检查连接」按钮 → 调 health
- 静态帮助：如何查 Mac IP、如何重新添加主屏幕、备份 `backend/data/` 提示（一句）

**明确不做：** 输入框修改服务器 URL。

## G2：App 壳 UI

### TabBar

| Tab | 标签 | 图标 |
|---|---|---|
| plan | 膳食计划 | 简单 SVG 或 Unicode（📅 类，优先 inline SVG） |
| recipes | 食谱 | 🍳 / SVG |
| journal | 饮食记录 | 📷 / SVG |
| shopping | 购物清单 | 🛒 / SVG |

- `min-height` 含 **safe-area-inset-bottom**
- 项高 ≥ 44px；当前路由 `NavLink` 高亮（品牌绿 `#2e7d32`）
- 主内容 `padding-bottom: calc(56px + env(safe-area-inset-bottom))`

### 页面调整

**MealPlanPage：**

- 移除 header 内「饮食记录」Link（改 Tab）
- 增加 ⚙ → `/settings`
- 保留「食谱」快捷 Link **可选删除**（Tab 已覆盖 → **删除** 减重复）

**JournalPage：**

- 移除「返回膳食计划」主按钮（Tab 切换）；可保留周导航

**ShoppingListPage：**

- 默认当前周（路由 `/shopping/:weekStart`）
- 移除「返回膳食计划」或改为弱提示；无清单时空状态 + 「前往膳食计划」链到 plan Tab
- 页内保留周 ◀ ▶

**RecipesPage：**

- 移除 toolbar「膳食计划」Link（Tab 覆盖）

**RecipeFormPage：**

- 仍在 Shell 内；Tab 高亮「食谱」

### PWA manifest / meta

`vite.config.ts` / `index.html`：

- `display: standalone`（已有）
- `theme_color: #2e7d32`，`background_color: #ffffff`
- `start_url: "/"`（由 `/` redirect 到本周计划）
- iOS：`apple-mobile-web-app-capable`、`apple-mobile-web-app-status-bar-style`、`apple-touch-icon`
- `viewport-fit=cover` 以启用 safe-area

### 启动加载

- health 检查期间：Shell 内或全屏 `zh.loading`（「加载中…」），避免白屏。

## 文件清单（实现参考）

| 文件 | 职责 |
|---|---|
| `frontend/src/components/AppShell.tsx` | 布局 + Outlet + TabBar |
| `frontend/src/components/TabBar.tsx` | 四 Tab NavLink |
| `frontend/src/components/ConnectionScreen.tsx` | 失败全屏 |
| `frontend/src/components/OfflineBanner.tsx` | 离线条 |
| `frontend/src/context/ConnectionContext.tsx` | health 状态与 retry |
| `frontend/src/pages/SettingsPage.tsx` | 设置/帮助 |
| `frontend/src/App.tsx` | 嵌套路由 refactor |
| `frontend/src/styles.css` | safe-area、tab-bar、connection-screen |
| `frontend/src/locale/zh.ts` | connection.* / settings.* / tabs.* |

**后端：** 无变更（`/api/health` 已存在）。

## 错误处理

| 场景 | 行为 |
|---|---|
| health 超时/非 200 | ConnectionScreen |
| 业务 API 失败 | 现有 `getErrorMessage()`，页面内 error |
| 离线 | 顶部 OfflineBanner + health 可能失败 |

## 测试

### Vitest
- `zh.tabs.*`、`zh.connection.*` keys 存在
- 手动：375×667；health 失败 UI；四 Tab；主屏幕 standalone；Tab 不遮挡底部横条

## Verify（手动）

1. `make build && make serve`，iPhone Safari 添加主屏幕
2. 打开图标 → 无 Safari 地址栏；四 Tab 切换正常
3. 停掉 `make serve` → 重开 App → ConnectionScreen；重试/复制可用
4. `/plan/xxx/shopping` 旧 URL 跳转到 `/shopping/xxx`
5. 购物清单 Tab 默认本周；无清单时空状态引导

## 相关文档

| 文档 | 用途 |
|---|---|
| [PLAN-v3-pwa.md](../../PLAN-v3-pwa.md) | 里程碑 |
| [SPEC.md](../../SPEC.md) | v3 完成后更新 PWA 能力描述 |
| [README.md](../../../README.md) | 安装与 troubleshooting |
