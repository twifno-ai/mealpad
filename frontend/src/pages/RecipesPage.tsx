import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, RECIPE_TYPES, type Recipe, type RecipeType } from "../api";

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [filter, setFilter] = useState<RecipeType | "">("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRecipes(await api.listRecipes(filter || undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(recipe: Recipe) {
    if (!confirm(`Delete "${recipe.name}"?`)) return;
    try {
      await api.deleteRecipe(recipe.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  const grouped = RECIPE_TYPES.map((type) => ({
    type,
    items: recipes.filter((r) => r.type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Recipes</h1>
        <Link to="/recipes/new" className="btn btn-primary">
          + New recipe
        </Link>
      </header>

      <div className="toolbar">
        <select
          className="input"
          value={filter}
          onChange={(e) => setFilter(e.target.value as RecipeType | "")}
          aria-label="Filter by type"
        >
          <option value="">All types</option>
          {RECIPE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <Link to="/plan" className="btn btn-secondary">
          Meal plan
        </Link>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading…</p>}

      {!loading && recipes.length === 0 && (
        <p className="muted">No recipes yet. Add your first one.</p>
      )}

      {grouped.map(({ type, items }) => (
        <section key={type} className="card-section">
          <h2 className="section-title">{type}</h2>
          <ul className="list">
            {items.map((recipe) => (
              <li key={recipe.id} className="list-row">
                <Link to={`/recipes/${recipe.id}/edit`} className="list-row-main">
                  <span className="list-row-title">{recipe.name}</span>
                  <span className="list-row-sub">
                    {recipe.ingredients.length} ingredients
                  </span>
                </Link>
                <button
                  type="button"
                  className="btn btn-danger btn-icon"
                  onClick={() => handleDelete(recipe)}
                  aria-label={`Delete ${recipe.name}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
