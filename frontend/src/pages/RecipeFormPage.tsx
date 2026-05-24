import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, CUISINE_TYPES, RECIPE_TYPES, type RecipeInput, type RecipeType, type CuisineType } from "../api";
import { cuisineLabel, recipeTypeLabel, zh } from "../locale/zh";

const emptyForm: RecipeInput = {
  name: "",
  description: "",
  type: "soup",
  cuisine: null,
  ingredients: [],
};

export default function RecipeFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);
  const [form, setForm] = useState(emptyForm);
  const [ingredientsText, setIngredientsText] = useState("");
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(isEdit);
  const [coverBusy, setCoverBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const recipe = await api.getRecipe(Number(id));
        setForm({
          name: recipe.name,
          description: recipe.description,
          type: recipe.type,
          cuisine: recipe.cuisine,
          ingredients: recipe.ingredients,
        });
        setIngredientsText(recipe.ingredients.join("\n"));
        setCoverUrl(recipe.cover_url);
      } catch (e) {
        console.error(e);
        setError(e instanceof Error ? e.message : zh.error.loadFailed);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  async function handleCoverChange(file: File | undefined) {
    if (!file || !id) return;
    setCoverBusy(true);
    setError("");
    try {
      const res = await api.uploadRecipeCover(Number(id), file);
      setCoverUrl(res.cover_url);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : zh.error.saveFailed);
    } finally {
      setCoverBusy(false);
    }
  }

  async function handleDeleteCover() {
    if (!id) return;
    setCoverBusy(true);
    setError("");
    try {
      await api.deleteRecipeCover(Number(id));
      setCoverUrl(null);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : zh.error.deleteFailed);
    } finally {
      setCoverBusy(false);
    }
  }

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
      console.error(err);
      setError(err instanceof Error ? err.message : zh.error.saveFailed);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p className="muted">{zh.loading}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>{isEdit ? zh.recipeForm.editTitle : zh.recipeForm.newTitle}</h1>
        <Link to="/recipes" className="btn btn-secondary">
          {zh.cancel}
        </Link>
      </header>

      {error && <p className="error">{error}</p>}

      <form className="form" onSubmit={handleSubmit}>
        <label className="field">
          <span>{zh.recipeForm.name}</span>
          <input
            className="input"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </label>

        <label className="field">
          <span>{zh.recipeForm.type}</span>
          <select
            className="input"
            value={form.type}
            onChange={(e) =>
              setForm({ ...form, type: e.target.value as RecipeType })
            }
          >
            {RECIPE_TYPES.map((t) => (
              <option key={t} value={t}>
                {recipeTypeLabel(t)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>{zh.recipeForm.cuisine}</span>
          <select
            className="input"
            value={form.cuisine ?? ""}
            onChange={(e) =>
              setForm({
                ...form,
                cuisine: (e.target.value || null) as CuisineType | null,
              })
            }
          >
            <option value="">{zh.recipeForm.unclassifiedCuisine}</option>
            {CUISINE_TYPES.map((c) => (
              <option key={c} value={c}>
                {cuisineLabel(c)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>{zh.recipeForm.description}</span>
          <textarea
            className="input"
            rows={3}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </label>

        {isEdit && (
          <div className="field">
            <span>{zh.recipeForm.cover}</span>
            {coverUrl && (
              <img src={coverUrl} alt="" className="recipe-cover-preview" />
            )}
            <input
              type="file"
              accept="image/*"
              className="input"
              disabled={coverBusy}
              onChange={(e) => handleCoverChange(e.target.files?.[0])}
            />
            {coverUrl && (
              <button
                type="button"
                className="btn btn-danger btn-block"
                disabled={coverBusy}
                onClick={handleDeleteCover}
              >
                {zh.recipeForm.removeCover}
              </button>
            )}
          </div>
        )}

        <label className="field">
          <span>{zh.recipeForm.ingredients}</span>
          <textarea
            className="input"
            rows={6}
            value={ingredientsText}
            onChange={(e) => setIngredientsText(e.target.value)}
          />
        </label>

        <button type="submit" className="btn btn-primary btn-block">
          {zh.save}
        </button>
      </form>
    </div>
  );
}
