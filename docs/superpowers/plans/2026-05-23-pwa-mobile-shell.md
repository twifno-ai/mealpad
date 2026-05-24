# v3 PWA Mobile Shell — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Mealpad PWA 做成 iPhone 主屏幕上的 App 级体验：health 连接引导 + 底部四 Tab，无需 Capacitor、不改后端。

**Architecture:** `ConnectionProvider` 包全局 health；失败时 `ConnectionScreen`；成功时 `AppShell`（`Outlet` + `TabBar`）。购物清单独立路由 `/shopping/:weekStart`。

**Tech Stack:** React Router nested routes、现有 Vite PWA、`/api/health`。

**Spec:** [docs/superpowers/specs/2026-05-23-pwa-mobile-shell-design.md](../specs/2026-05-23-pwa-mobile-shell-design.md)  
**Milestones:** [docs/PLAN-v3-pwa.md](../../PLAN-v3-pwa.md)

---

## File map

| File | Responsibility |
|---|---|
| `frontend/src/context/ConnectionContext.tsx` | health fetch、online 状态、retry |
| `frontend/src/components/ConnectionScreen.tsx` | 全屏失败 UI |
| `frontend/src/components/OfflineBanner.tsx` | 离线条 |
| `frontend/src/pages/SettingsPage.tsx` | 地址、复制、帮助 |
| `frontend/src/components/AppShell.tsx` | shell 布局 + Outlet |
| `frontend/src/components/TabBar.tsx` | 四 Tab NavLink |
| `frontend/src/App.tsx` | 嵌套路由 |
| `frontend/src/main.tsx` | 包裹 ConnectionProvider |
| `frontend/src/locale/zh.ts` | tabs / connection / settings |
| `frontend/vite.config.ts` | manifest start_url |
| `frontend/index.html` | viewport-fit、apple meta |

---

### Task 1: ConnectionContext 与 health 检查（V3-M1）

**Files:**
- Create: `frontend/src/context/ConnectionContext.tsx`
- Create: `frontend/src/api/health.ts`（可选小模块，或 inline 在 context）
- Modify: `frontend/src/locale/zh.ts`
- Modify: `frontend/src/locale/zh.test.ts`

- [ ] **Step 1: 写失败测试（locale keys）**

```typescript
// frontend/src/locale/zh.test.ts — append
import { zh } from "./zh";

describe("v3 connection and tabs", () => {
  it("has connection strings", () => {
    expect(zh.connection.title).toBeTruthy();
    expect(zh.connection.retry).toBeTruthy();
  });
  it("has tab labels", () => {
    expect(zh.tabs.plan).toBe("膳食计划");
    expect(zh.tabs.shopping).toBe("购物清单");
  });
});
```

Run: `cd frontend && npm test` → FAIL（keys 不存在）

- [ ] **Step 2: 添加 zh 文案**

```typescript
// frontend/src/locale/zh.ts — append before `} as const`
tabs: {
  plan: "膳食计划",
  recipes: "食谱",
  journal: "饮食记录",
  shopping: "购物清单",
},
connection: {
  title: "无法连接 Mealpad 服务器",
  hint: "请确认手机与运行 Mealpad 的电脑在同一 Wi‑Fi。",
  checkServe: "在电脑上运行 make serve",
  checkIp: "若 Mac IP 变了，请用 Safari 打开新地址并重新「添加到主屏幕」",
  retry: "重试",
  copyAddress: "复制当前地址",
  helpTitle: "连接帮助",
  helpBody:
    "1. 电脑与手机同一 Wi‑Fi\n2. 终端执行 make build && make serve\n3. macOS 查 IP：ipconfig getifaddr en0\n4. Safari 打开 http://<IP>:8000 并添加到主屏幕",
  copied: "已复制",
  offline: "当前无网络",
},
settings: {
  title: "设置",
  serverAddress: "服务器地址",
  checkConnection: "检查连接",
  connected: "连接正常",
  failed: "无法连接",
  backupHint: "备份请拷贝电脑上的 backend/data/ 目录。",
},
```

- [ ] **Step 3: 实现 health 与 Context**

```typescript
// frontend/src/context/ConnectionContext.tsx
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const HEALTH_TIMEOUT_MS = 3000;

type Status = "checking" | "ok" | "failed";

type ConnectionContextValue = {
  status: Status;
  online: boolean;
  retry: () => void;
};

const ConnectionContext = createContext<ConnectionContextValue | null>(null);

async function pingHealth(): Promise<boolean> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const res = await fetch("/api/health", { signal: controller.signal });
    if (!res.ok) return false;
    const body = await res.json();
    return body?.ok === true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("checking");
  const [online, setOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );

  const check = useCallback(async () => {
    setStatus("checking");
    const ok = await pingHealth();
    setStatus(ok ? "ok" : "failed");
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  useEffect(() => {
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  const value = useMemo(
    () => ({ status, online, retry: check }),
    [status, online, check],
  );

  return (
    <ConnectionContext.Provider value={value}>{children}</ConnectionContext.Provider>
  );
}

export function useConnection() {
  const ctx = useContext(ConnectionContext);
  if (!ctx) throw new Error("useConnection outside ConnectionProvider");
  return ctx;
}
```

- [ ] **Step 4: npm test PASS**

Run: `cd frontend && npm test`

- [ ] **Step 5: Commit + push**

```bash
git add frontend/src/context/ConnectionContext.tsx frontend/src/locale/zh.ts frontend/src/locale/zh.test.ts
git commit -m "feat(v3): connection context and locale strings for health check"
git push
```

---

### Task 2: ConnectionScreen、OfflineBanner、SettingsPage（V3-M1 续）

**Files:**
- Create: `frontend/src/components/ConnectionScreen.tsx`
- Create: `frontend/src/components/OfflineBanner.tsx`
- Create: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`（临时直接渲染 Settings 路由测试）
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: ConnectionScreen**

```tsx
// frontend/src/components/ConnectionScreen.tsx
import { useState } from "react";
import { useConnection } from "../context/ConnectionContext";
import { zh } from "../locale/zh";

export default function ConnectionScreen() {
  const { retry, status } = useConnection();
  const [showHelp, setShowHelp] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copyOrigin() {
    await navigator.clipboard.writeText(window.location.origin);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="connection-screen">
      <h1>{zh.connection.title}</h1>
      <p>{zh.connection.hint}</p>
      <ul className="connection-checklist">
        <li>{zh.connection.checkServe}</li>
        <li>{zh.connection.checkIp}</li>
      </ul>
      <button type="button" className="btn btn-primary btn-block" onClick={retry} disabled={status === "checking"}>
        {status === "checking" ? zh.loading : zh.connection.retry}
      </button>
      <button type="button" className="btn btn-secondary btn-block" onClick={copyOrigin}>
        {copied ? zh.connection.copied : zh.connection.copyAddress}
      </button>
      <button type="button" className="btn btn-secondary btn-block" onClick={() => setShowHelp((v) => !v)}>
        {zh.connection.helpTitle}
      </button>
      {showHelp && <pre className="connection-help">{zh.connection.helpBody}</pre>}
    </div>
  );
}
```

- [ ] **Step 2: OfflineBanner**

```tsx
// frontend/src/components/OfflineBanner.tsx
import { useConnection } from "../context/ConnectionContext";
import { zh } from "../locale/zh";

export default function OfflineBanner() {
  const { online } = useConnection();
  if (online) return null;
  return <div className="offline-banner">{zh.connection.offline}</div>;
}
```

- [ ] **Step 3: SettingsPage**

```tsx
// frontend/src/pages/SettingsPage.tsx
import { Link } from "react-router-dom";
import { useConnection } from "../context/ConnectionContext";
import { formatIsoDate, mondayOfWeek } from "../api";
import { zh } from "../locale/zh";

export default function SettingsPage() {
  const { status, retry } = useConnection();
  const origin = window.location.origin;
  const week = formatIsoDate(mondayOfWeek(new Date()));

  return (
    <div className="page">
      <header className="page-header">
        <h1>{zh.settings.title}</h1>
        <Link to={`/plan/${week}`} className="btn btn-secondary">
          {zh.back}
        </Link>
      </header>
      <p className="muted">{zh.settings.serverAddress}</p>
      <p className="settings-origin">{origin}</p>
      <button type="button" className="btn btn-secondary btn-block" onClick={() => navigator.clipboard.writeText(origin)}>
        {zh.connection.copyAddress}
      </button>
      <button type="button" className="btn btn-primary btn-block" onClick={retry}>
        {zh.settings.checkConnection}
      </button>
      <p className="muted">
        {status === "ok" ? zh.settings.connected : status === "failed" ? zh.settings.failed : zh.loading}
      </p>
      <pre className="connection-help">{zh.connection.helpBody}</pre>
      <p className="muted">{zh.settings.backupHint}</p>
    </div>
  );
}
```

- [ ] **Step 4: main.tsx 包裹 Provider；App 根层 gate**

```tsx
// frontend/src/main.tsx
import { ConnectionProvider } from "./context/ConnectionContext";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <ConnectionProvider>
        <App />
      </ConnectionProvider>
    </BrowserRouter>
  </StrictMode>,
);
```

```tsx
// frontend/src/App.tsx — 在 Routes 外包一层（Task 3 会 refactor，此处先最小 gate）
import ConnectionScreen from "./components/ConnectionScreen";
import { useConnection } from "./context/ConnectionContext";

function AppGate({ children }: { children: React.ReactNode }) {
  const { status } = useConnection();
  if (status === "checking") {
    return (
      <div className="page">
        <p className="muted">{zh.loading}</p>
      </div>
    );
  }
  if (status === "failed") return <ConnectionScreen />;
  return <>{children}</>;
}
```

- [ ] **Step 5: CSS**

```css
.connection-screen {
  min-height: 100dvh;
  padding: 1.5rem;
  padding-top: max(1.5rem, env(safe-area-inset-top));
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.connection-checklist { margin: 0; padding-left: 1.25rem; }
.connection-help {
  white-space: pre-wrap;
  font-size: 0.875rem;
  background: #f5f5f5;
  padding: 0.75rem;
  border-radius: 8px;
}
.offline-banner {
  position: sticky;
  top: 0;
  z-index: 50;
  background: #fff3e0;
  color: #e65100;
  text-align: center;
  padding: 0.5rem;
  font-size: 0.875rem;
}
.settings-origin {
  font-family: ui-monospace, monospace;
  word-break: break-all;
}
```

- [ ] **Step 6: npm test && npm run build**

- [ ] **Step 7: Commit + push**

```bash
git commit -m "feat(v3): connection screen, offline banner, and settings page"
git push
```

---

### Task 3: AppShell 与 TabBar（V3-M2）

**Files:**
- Create: `frontend/src/components/AppShell.tsx`
- Create: `frontend/src/components/TabBar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: TabBar**

```tsx
// frontend/src/components/TabBar.tsx
import { NavLink, useLocation } from "react-router-dom";
import { formatIsoDate, mondayOfWeek } from "../api";
import { zh } from "../locale/zh";

const defaultWeek = formatIsoDate(mondayOfWeek(new Date()));

const TABS = [
  { key: "plan", label: zh.tabs.plan, to: `/plan/${defaultWeek}`, match: /^\/plan(\/|$)/ },
  { key: "recipes", label: zh.tabs.recipes, to: "/recipes", match: /^\/recipes(\/|$)/ },
  { key: "journal", label: zh.tabs.journal, to: `/journal/${defaultWeek}`, match: /^\/journal(\/|$)/ },
  { key: "shopping", label: zh.tabs.shopping, to: `/shopping/${defaultWeek}`, match: /^\/shopping(\/|$)/ },
] as const;

export default function TabBar() {
  const { pathname } = useLocation();

  function isActive(match: RegExp) {
    if (match.test(pathname)) return true;
    // 食谱表单仍高亮食谱 Tab
    if (match.source.startsWith("^\\/recipes") && pathname.startsWith("/recipes")) return true;
    return false;
  }

  return (
    <nav className="tab-bar" aria-label="主导航">
      {TABS.map((tab) => (
        <NavLink
          key={tab.key}
          to={tab.to}
          className={() => `tab-bar-item ${isActive(tab.match) ? "active" : ""}`}
        >
          <span className="tab-bar-label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: AppShell**

```tsx
// frontend/src/components/AppShell.tsx
import { Outlet } from "react-router-dom";
import OfflineBanner from "./OfflineBanner";
import TabBar from "./TabBar";

export default function AppShell() {
  return (
    <div className="app-shell">
      <OfflineBanner />
      <main className="app-shell-main">
        <Outlet />
      </main>
      <TabBar />
    </div>
  );
}
```

- [ ] **Step 3: App.tsx 嵌套路由**

```tsx
// frontend/src/App.tsx
import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import ConnectionScreen from "./components/ConnectionScreen";
import { useConnection } from "./context/ConnectionContext";
import JournalPage from "./pages/JournalPage";
import MealPlanPage from "./pages/MealPlanPage";
import RecipeFormPage from "./pages/RecipeFormPage";
import RecipesPage from "./pages/RecipesPage";
import SettingsPage from "./pages/SettingsPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import { formatIsoDate, mondayOfWeek } from "./api";
import { zh } from "./locale/zh";

const defaultWeek = formatIsoDate(mondayOfWeek(new Date()));

function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Navigate to={`/plan/${defaultWeek}`} replace />} />
        <Route path="/plan" element={<Navigate to={`/plan/${defaultWeek}`} replace />} />
        <Route path="/plan/:weekStart" element={<MealPlanPage />} />
        <Route path="/plan/:weekStart/shopping" element={<RedirectShopping />} />
        <Route path="/recipes" element={<RecipesPage />} />
        <Route path="/recipes/new" element={<RecipeFormPage />} />
        <Route path="/recipes/:id/edit" element={<RecipeFormPage />} />
        <Route path="/journal" element={<Navigate to={`/journal/${defaultWeek}`} replace />} />
        <Route path="/journal/:weekStart" element={<JournalPage />} />
        <Route path="/shopping" element={<Navigate to={`/shopping/${defaultWeek}`} replace />} />
        <Route path="/shopping/:weekStart" element={<ShoppingListPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}

function RedirectShopping() {
  const { weekStart } = useParams();
  return <Navigate to={`/shopping/${weekStart}`} replace />;
}

export default function App() {
  const { status } = useConnection();
  if (status === "checking") {
    return (
      <div className="page">
        <p className="muted">{zh.loading}</p>
      </div>
    );
  }
  if (status === "failed") return <ConnectionScreen />;
  return <AppRoutes />;
}
```

Add `import { Navigate, Route, Routes, useParams } from "react-router-dom";`

- [ ] **Step 4: TabBar CSS**

```css
.app-shell {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}
.app-shell-main {
  flex: 1;
  padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px));
}
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  background: #fff;
  border-top: 1px solid #e0e0e0;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  z-index: 40;
}
.tab-bar-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 56px;
  font-size: 0.75rem;
  color: #666;
  text-decoration: none;
}
.tab-bar-item.active {
  color: #2e7d32;
  font-weight: 600;
}
```

- [ ] **Step 5: npm test && npm run build**

- [ ] **Step 6: Commit + push**

```bash
git commit -m "feat(v3): bottom tab bar and app shell layout"
git push
```

---

### Task 4: 页面适配与购物清单路由（V3-M3）

**Files:**
- Modify: `frontend/src/pages/MealPlanPage.tsx`
- Modify: `frontend/src/pages/JournalPage.tsx`
- Modify: `frontend/src/pages/RecipesPage.tsx`
- Modify: `frontend/src/pages/ShoppingListPage.tsx`
- Modify: `frontend/src/locale/zh.ts`

- [ ] **Step 1: MealPlanPage header**

移除 `Link` 到 `/journal` 和 `/recipes`；改为：

```tsx
import { Link } from "react-router-dom";
// header:
<div className="header-actions">
  <Link to="/settings" className="btn btn-secondary btn-icon" aria-label={zh.settings.title}>
    ⚙
  </Link>
</div>
```

购物清单按钮：`navigate(\`/shopping/${startIso}\`)` 替代 `/plan/${startIso}/shopping`

- [ ] **Step 2: JournalPage**

删除 header 中 `Link to={/plan/${startIso}}` 的「返回膳食计划」按钮；保留标题与周导航。

- [ ] **Step 3: RecipesPage**

删除 toolbar 中 `Link to="/plan"`。

- [ ] **Step 4: ShoppingListPage**

```tsx
// 参数 weekStart 已从 /shopping/:weekStart 读取（已有逻辑复用）
// header：删除 backToPlan Link，或改为：
{!list && !loading && (
  <p className="muted">
    {zh.shopping.empty}{" "}
    <Link to={`/plan/${startIso}`}>{zh.shopping.goToPlan}</Link>
  </p>
)}
```

Add to zh.shopping: `goToPlan: "前往膳食计划"`

- [ ] **Step 5: 全局搜索替换**

```bash
rg "/plan/.*/shopping" frontend/src
```

确保无残留旧路径（MealPlanPage handleShoppingAction 等）。

- [ ] **Step 6: npm test && npm run build**

- [ ] **Step 7: Commit + push**

```bash
git commit -m "feat(v3): adapt pages for tab navigation and shopping route"
git push
```

---

### Task 5: PWA manifest 与 iOS meta（V3-M4）

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/index.html`

- [ ] **Step 1: index.html**

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<meta name="apple-mobile-web-app-capable" content="yes" />
<meta name="apple-mobile-web-app-status-bar-style" content="default" />
<link rel="apple-touch-icon" href="/icon-192.png" />
```

- [ ] **Step 2: vite.config.ts**

```typescript
manifest: {
  // ...existing
  start_url: "/",
  scope: "/",
}
```

- [ ] **Step 3: make build；确认 dist manifest.json start_url 为 `/`**

Run: `cd frontend && npm run build && cat dist/manifest.webmanifest | head`

- [ ] **Step 4: Commit + push**

```bash
git commit -m "feat(v3): polish PWA manifest and iOS standalone meta"
git push
```

---

### Task 6: 文档与全量验证（V3-M5）

**Files:**
- Modify: `docs/SPEC.md`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-23-pwa-mobile-shell-design.md`（状态 → 已完成）
- Modify: `docs/PLAN-v3-pwa.md`（链到本 plan）

- [ ] **Step 1: SPEC 增加 PWA App 壳条目**

Core capabilities 增加：底部 Tab 导航、连接 health 引导、设置页。

- [ ] **Step 2: README**

「Production / LAN」节强调：添加主屏幕后以四 Tab 使用；无法连接时看重试屏说明。

- [ ] **Step 3: 全量验证**

```bash
cd backend && MEALPAD_TESTING=1 .venv/bin/pytest -q
cd frontend && npm test && npm run build
make build && make serve
```

手动：iPhone 主屏幕；四 Tab；停 serve 见 ConnectionScreen。

- [ ] **Step 4: Commit + push**

```bash
git commit -m "docs: update SPEC and README for v3 PWA mobile shell"
git push
```

---

## Spec coverage checklist

| Spec 要求 | Task |
|---|---|
| health 3s timeout | Task 1 |
| ConnectionScreen 中文引导 | Task 2 |
| SettingsPage | Task 2 |
| OfflineBanner | Task 2 |
| 四 Tab | Task 3 |
| safe-area padding | Task 3 CSS |
| `/shopping/:week` | Task 3–4 |
| 旧 shopping redirect | Task 3 |
| 页面去重复 nav | Task 4 |
| manifest / iOS meta | Task 5 |
| 文档 | Task 6 |

## 全量回归

- [ ] v2 标记已做 / 封面上传正常
- [ ] AI fill / regenerate / 购物清单生成
- [ ] `/recipes/1/edit` 深链
- [ ] `npm run dev` + proxy 开发模式
