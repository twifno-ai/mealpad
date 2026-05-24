import { ApiError } from "./httpErrors";

export { ApiError, formatHttpError } from "./httpErrors";

export type RecipeType = "soup" | "meat" | "veg" | "other";

export const RECIPE_TYPES: RecipeType[] = ["soup", "meat", "veg", "other"];

export interface Recipe {
  id: number;
  name: string;
  description: string;
  type: RecipeType;
  ingredients: string[];
  created_at: string;
}

export interface RecipeInput {
  name: string;
  description: string;
  type: RecipeType;
  ingredients: string[];
}

export interface RecipeSummary {
  id: number;
  name: string;
  type: string;
}

export interface MealPlanEntry {
  id: number;
  date: string;
  slot: "lunch" | "dinner";
  recipe_id: number;
  sort_order: number;
  recipe: RecipeSummary;
  created_at: string;
}

export interface ShoppingListItem {
  id: number;
  text: string;
  category: string;
  checked: boolean;
}

export interface ShoppingList {
  id: number;
  start_date: string;
  end_date: string;
  generated_at: string;
  items_by_category: Record<string, ShoppingListItem[]>;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  listRecipes: (type?: RecipeType) =>
    req<Recipe[]>(`/api/recipes${type ? `?type=${type}` : ""}`),
  getRecipe: (id: number) => req<Recipe>(`/api/recipes/${id}`),
  createRecipe: (body: RecipeInput) =>
    req<Recipe>("/api/recipes", { method: "POST", body: JSON.stringify(body) }),
  updateRecipe: (id: number, body: RecipeInput) =>
    req<Recipe>(`/api/recipes/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  deleteRecipe: (id: number) =>
    req<void>(`/api/recipes/${id}`, { method: "DELETE" }),

  getMealPlan: (start: string, end: string) =>
    req<MealPlanEntry[]>(`/api/meal-plan?start=${start}&end=${end}`),
  addMealPlanItem: (date: string, slot: string, recipeId: number) =>
    req<MealPlanEntry>(`/api/meal-plan/${date}/${slot}/items`, {
      method: "POST",
      body: JSON.stringify({ recipe_id: recipeId }),
    }),
  updateMealPlanItem: (entryId: number, recipeId: number) =>
    req<MealPlanEntry>(`/api/meal-plan/items/${entryId}`, {
      method: "PUT",
      body: JSON.stringify({ recipe_id: recipeId }),
    }),
  deleteMealPlanItem: (entryId: number) =>
    req<void>(`/api/meal-plan/items/${entryId}`, { method: "DELETE" }),
  deleteMealPlanSlot: (date: string, slot: string) =>
    req<void>(`/api/meal-plan/${date}/${slot}`, { method: "DELETE" }),
  generateMealPlan: (start: string, end: string) =>
    req<MealPlanEntry[]>("/api/meal-plan/generate", {
      method: "POST",
      body: JSON.stringify({ start, end }),
    }),
  regenerateMealPlan: (start: string, end: string) =>
    req<MealPlanEntry[]>("/api/meal-plan/regenerate", {
      method: "POST",
      body: JSON.stringify({ start, end }),
    }),

  getShoppingList: (start: string, end: string) =>
    req<ShoppingList>(`/api/shopping-lists?start=${start}&end=${end}`),
  generateShoppingList: (start: string, end: string) =>
    req<ShoppingList>("/api/shopping-lists", {
      method: "POST",
      body: JSON.stringify({ start, end }),
    }),
  toggleShoppingItem: (id: number, checked: boolean) =>
    req<ShoppingListItem>(`/api/shopping-list-items/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ checked }),
    }),
};

export function mondayOfWeek(d: Date): Date {
  const copy = new Date(d);
  const day = copy.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  copy.setDate(copy.getDate() + diff);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

export function addDays(d: Date, n: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + n);
  return copy;
}

export function formatIsoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}
