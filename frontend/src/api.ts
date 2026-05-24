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
  cover_url: string | null;
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
  cover_url?: string | null;
}

export interface CookedDishLog {
  id: number;
  date: string;
  slot: "lunch" | "dinner";
  recipe_id: number | null;
  recipe_name: string;
  kind: "planned" | "extra";
  meal_plan_entry_id: number | null;
  photo_url: string | null;
  logged_at: string;
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
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

async function reqForm<T>(path: string, form: FormData, method = "POST"): Promise<T> {
  const res = await fetch(path, { method, body: form });
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
  uploadRecipeCover: (id: number, photo: File) => {
    const form = new FormData();
    form.append("photo", photo);
    return reqForm<{ cover_url: string }>(`/api/recipes/${id}/cover`, form);
  },
  deleteRecipeCover: (id: number) =>
    req<void>(`/api/recipes/${id}/cover`, { method: "DELETE" }),

  getCookedDishes: (start: string, end: string) =>
    req<CookedDishLog[]>(`/api/cooked-dishes?start=${start}&end=${end}`),
  markPlannedCooked: (entryId: number, photo?: File) => {
    const form = new FormData();
    if (photo) form.append("photo", photo);
    return reqForm<CookedDishLog>(`/api/cooked-dishes/planned/${entryId}`, form);
  },
  addExtraCooked: (date: string, slot: string, recipeId: number, photo?: File) => {
    const form = new FormData();
    form.append("date", date);
    form.append("slot", slot);
    form.append("recipe_id", String(recipeId));
    if (photo) form.append("photo", photo);
    return reqForm<CookedDishLog>("/api/cooked-dishes/extra", form);
  },
  replaceCookedPhoto: (logId: number, photo: File) => {
    const form = new FormData();
    form.append("photo", photo);
    return reqForm<CookedDishLog>(`/api/cooked-dishes/${logId}/photo`, form, "PUT");
  },
  deleteCookedPhoto: (logId: number) =>
    req<CookedDishLog>(`/api/cooked-dishes/${logId}/photo`, { method: "DELETE" }),
  deleteCookedLog: (logId: number) =>
    req<void>(`/api/cooked-dishes/${logId}`, { method: "DELETE" }),

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
