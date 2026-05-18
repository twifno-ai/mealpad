import { Navigate, Route, Routes } from "react-router-dom";
import MealPlanPage from "./pages/MealPlanPage";
import RecipeFormPage from "./pages/RecipeFormPage";
import RecipesPage from "./pages/RecipesPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import { formatIsoDate, mondayOfWeek } from "./api";

const defaultWeek = formatIsoDate(mondayOfWeek(new Date()));

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to={`/plan/${defaultWeek}`} replace />} />
      <Route path="/recipes" element={<RecipesPage />} />
      <Route path="/recipes/new" element={<RecipeFormPage />} />
      <Route path="/recipes/:id/edit" element={<RecipeFormPage />} />
      <Route path="/plan" element={<Navigate to={`/plan/${defaultWeek}`} replace />} />
      <Route path="/plan/:weekStart" element={<MealPlanPage />} />
      <Route path="/plan/:weekStart/shopping" element={<ShoppingListPage />} />
    </Routes>
  );
}
