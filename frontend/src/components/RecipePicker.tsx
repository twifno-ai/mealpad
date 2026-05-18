import { useEffect, useState } from "react";
import { api, type Recipe } from "../api";

interface Props {
  onSelect: (recipeId: number) => void;
  onClear: () => void;
  onClose: () => void;
}

export default function RecipePicker({ onSelect, onClear, onClose }: Props) {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.listRecipes().then(setRecipes).catch((e) => setError(e.message));
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
        aria-label="Pick a recipe"
      >
        <header className="modal-header">
          <h2>Choose recipe</h2>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </header>

        <input
          className="input"
          placeholder="Search recipes…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />

        {error && <p className="error">{error}</p>}

        <button type="button" className="btn btn-danger btn-block" onClick={onClear}>
          Clear slot
        </button>

        <ul className="list picker-list">
          {filtered.map((recipe) => (
            <li key={recipe.id}>
              <button
                type="button"
                className="list-row-main picker-item"
                onClick={() => onSelect(recipe.id)}
              >
                <span className="list-row-title">{recipe.name}</span>
                <span className="list-row-sub">{recipe.type}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
