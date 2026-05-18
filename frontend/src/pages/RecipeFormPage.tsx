import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, RECIPE_TYPES, type RecipeInput, type RecipeType } from "../api";

const emptyForm: RecipeInput = {
  name: "",
  description: "",
  type: "soup",
  ingredients: [],
};

export default function RecipeFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);
  const [form, setForm] = useState(emptyForm);
  const [ingredientsText, setIngredientsText] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(isEdit);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const recipe = await api.getRecipe(Number(id));
        setForm({
          name: recipe.name,
          description: recipe.description,
          type: recipe.type,
          ingredients: recipe.ingredients,
        });
        setIngredientsText(recipe.ingredients.join("\n"));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const body: RecipeInput = {
      ...form,
      ingredients: ingredientsText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
    };
    try {
      if (isEdit && id) {
        await api.updateRecipe(Number(id), body);
      } else {
        await api.createRecipe(body);
      }
      navigate("/recipes");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p className="muted">Loading…</p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>{isEdit ? "Edit recipe" : "New recipe"}</h1>
        <Link to="/recipes" className="btn btn-secondary">
          Cancel
        </Link>
      </header>

      {error && <p className="error">{error}</p>}

      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span>Name</span>
          <input
            className="input"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </label>

        <label className="field">
          <span>Type</span>
          <select
            className="input"
            value={form.type}
            onChange={(e) =>
              setForm({ ...form, type: e.target.value as RecipeType })
            }
          >
            {RECIPE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Description</span>
          <textarea
            className="input"
            rows={3}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </label>

        <label className="field">
          <span>Ingredients (one per line)</span>
          <textarea
            className="input"
            rows={6}
            value={ingredientsText}
            onChange={(e) => setIngredientsText(e.target.value)}
          />
        </label>

        <button type="submit" className="btn btn-primary btn-block">
          Save
        </button>
      </form>
    </div>
  );
}
