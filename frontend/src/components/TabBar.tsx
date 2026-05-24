import { NavLink, useLocation } from "react-router-dom";
import { formatIsoDate, mondayOfWeek } from "../api";
import { zh } from "../locale/zh";

const defaultWeek = formatIsoDate(mondayOfWeek(new Date()));

const TABS = [
  {
    key: "plan",
    label: zh.tabs.plan,
    to: `/plan/${defaultWeek}`,
    match: (path: string) => path.startsWith("/plan"),
  },
  {
    key: "recipes",
    label: zh.tabs.recipes,
    to: "/recipes",
    match: (path: string) => path.startsWith("/recipes"),
  },
  {
    key: "journal",
    label: zh.tabs.journal,
    to: `/journal/${defaultWeek}`,
    match: (path: string) => path.startsWith("/journal"),
  },
  {
    key: "shopping",
    label: zh.tabs.shopping,
    to: `/shopping/${defaultWeek}`,
    match: (path: string) => path.startsWith("/shopping"),
  },
] as const;

export default function TabBar() {
  const { pathname } = useLocation();

  return (
    <nav className="tab-bar" aria-label="主导航">
      {TABS.map((tab) => (
        <NavLink
          key={tab.key}
          to={tab.to}
          className={() => `tab-bar-item ${tab.match(pathname) ? "active" : ""}`}
        >
          <span className="tab-bar-label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
