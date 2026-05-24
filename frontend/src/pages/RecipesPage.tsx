import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  CUISINE_TYPES,
  RECIPE_TYPES,
  type CuisineType,
  type Recipe,
  type RecipeType,
} from "../api";
import { cuisineLabel, recipeTypeLabel, zh } from "../locale/zh";

type CuisineFilter = CuisineType | "" | "unset";

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [typeFilter, setTypeFilter] = useState<RecipeType | "">("");
  const [cuisineFilter, setCuisineFilter] = useState<CuisineFilter>("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const cuisineParam =
        cuisineFilter === ""
          ? undefined
          : cuisineFilter === "unset"
            ? ""
            : cuisineFilter;
      setRecipes(await api.listRecipes(typeFilter || undefined, cuisineParam));
    } catch (e) {
      console.error(e);
      setError(zh.error.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [typeFilter, cuisineFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(recipe: Recipe) {
    if (!confirm(zh.recipes.deleteConfirm(recipe.name))) return;
    try {
      await api.deleteRecipe(recipe.id);
      await load();
    } catch (e) {
      console.error(e);
      setError(zh.error.deleteFailed);
    }
  }

  const grouped = RECIPE_TYPES.map((type) => ({
    type,
    items: recipes.filter((r) => r.type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="page">
      <header className="page-header">
        <h1>{zh.recipes.title}</h1>
        <Link to="/recipes/new" className="btn btn-primary">
          {zh.recipes.new}
        </Link>
      </header>

      <div className="toolbar">
        <select
          className="input"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as RecipeType | "")}
          aria-label={zh.recipes.filterByType}
        >
          <option value="">{zh.recipes.allTypes}</option>
          {RECIPE_TYPES.map((t) => (
            <option key={t} value={t}>
              {recipeTypeLabel(t)}
            </option>
          ))}
        </select>
        <select
          className="input"
          value={cuisineFilter}
          onChange={(e) => setCuisineFilter(e.target.value as CuisineFilter)}
          aria-label={zh.recipes.filterByCuisine}
        >
          <option value="">{zh.recipes.allCuisines}</option>
          <option value="unset">{zh.recipes.unclassifiedCuisine}</option>
          {CUISINE_TYPES.map((c) => (
            <option key={c} value={c}>
              {cuisineLabel(c)}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">{zh.loading}</p>}

      {!loading && recipes.length === 0 && (
        <p className="muted">{zh.recipes.empty}</p>
      )}

      {grouped.map(({ type, items }) => (
        <section key={type} className="card-section">
          <h2 className="section-title">{recipeTypeLabel(type)}</h2>
          <ul className="list">
            {items.map((recipe) => (
              <li key={recipe.id} className="list-row">
                <Link to={`/recipes/${recipe.id}/edit`} className="list-row-main">
                  {recipe.cover_url && (
                    <img src={recipe.cover_url} alt="" className="recipe-list-thumb" />
                  )}
                  <span className="list-row-text">
                    <span className="list-row-title">{recipe.name}</span>
                    <span className="list-row-sub">
                      {cuisineLabel(recipe.cuisine)} ·{" "}
                      {zh.recipes.ingredientsCount(recipe.ingredients.length)}
                    </span>
                  </span>
                </Link>
                <button
                  type="button"
                  className="btn btn-danger btn-icon"
                  onClick={() => handleDelete(recipe)}
                  aria-label={`${zh.delete} ${recipe.name}`}
                >
                  {zh.delete}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
