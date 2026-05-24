import { Navigate, Route, Routes, useParams } from "react-router-dom";
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

function RedirectShopping() {
  const { weekStart } = useParams();
  return <Navigate to={`/shopping/${weekStart ?? defaultWeek}`} replace />;
}

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
