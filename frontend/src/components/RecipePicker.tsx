import { useEffect, useState } from "react";
import { api, type Recipe } from "../api";
import { recipeTypeLabel, zh } from "../locale/zh";

interface Props {
  title?: string;
  showClear?: boolean;
  onSelect: (recipeId: number) => void;
  onClear?: () => void;
  onClose: () => void;
}

export default function RecipePicker({
  title,
  showClear = true,
  onSelect,
  onClear,
  onClose,
}: Props) {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listRecipes()
      .then(setRecipes)
      .catch((e) => {
        console.error(e);
        setError(zh.error.loadFailed);
      });
  }, []);

  const filtered = recipes.filter((r) =>
    r.name.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={zh.picker.title}
      >
        <header className="modal-header">
          <h2>{title ?? zh.picker.title}</h2>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            {zh.close}
          </button>
        </header>

        <input
          className="input"
          placeholder={zh.picker.search}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />

        {error && <p className="error">{error}</p>}

        {showClear && onClear && (
          <button type="button" className="btn btn-danger btn-block" onClick={onClear}>
            {zh.picker.clearSlot}
          </button>
        )}

        <ul className="list picker-list">
          {filtered.map((recipe) => (
            <li key={recipe.id}>
              <button
                type="button"
                className="list-row-main picker-item"
                onClick={() => onSelect(recipe.id)}
              >
                <span className="list-row-title">{recipe.name}</span>
                <span className="list-row-sub">{recipeTypeLabel(recipe.type)}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
