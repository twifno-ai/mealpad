import { useState } from "react";
import { type MealPlanEntry } from "../api";
import { recipeTypeLabel, slotLabel, zh } from "../locale/zh";

interface Props {
  date: string;
  slot: string;
  entries: MealPlanEntry[];
  onAdd: () => void;
  onReplace: (entryId: number) => void;
  onRemove: (entryId: number) => Promise<void>;
  onClearMeal: () => Promise<void>;
  onClose: () => void;
}

export default function MealSlotModal({
  date,
  slot,
  entries,
  onAdd,
  onReplace,
  onRemove,
  onClearMeal,
  onClose,
}: Props) {
  const [error, setError] = useState("");

  async function handleRemove(entryId: number) {
    setError("");
    try {
      await onRemove(entryId);
    } catch (e) {
      console.error(e);
      setError(zh.error.generic);
    }
  }

  async function handleClear() {
    if (!confirm(zh.picker.clearSlot)) return;
    setError("");
    try {
      await onClearMeal();
    } catch (e) {
      console.error(e);
      setError(zh.error.generic);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={zh.mealPlan.mealDetail}
      >
        <header className="modal-header">
          <h2>
            {date} · {slotLabel(slot)}
          </h2>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            {zh.close}
          </button>
        </header>

        {error && <p className="error">{error}</p>}

        {entries.length === 0 ? (
          <p className="muted">{zh.mealPlan.emptyMeal}</p>
        ) : (
          <ul className="list meal-dish-list">
            {entries.map((entry) => (
              <li key={entry.id} className="meal-dish-row">
                <div className="meal-dish-info">
                  <span className="list-row-title">{entry.recipe.name}</span>
                  <span className="list-row-sub">{recipeTypeLabel(entry.recipe.type)}</span>
                </div>
                <div className="meal-dish-actions">
                  <button
                    type="button"
                    className="btn btn-secondary btn-icon"
                    onClick={() => onReplace(entry.id)}
                  >
                    {zh.mealPlan.replaceDish}
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger btn-icon"
                    onClick={() => handleRemove(entry.id)}
                  >
                    {zh.mealPlan.removeDish}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <button type="button" className="btn btn-primary btn-block" onClick={onAdd}>
          {zh.mealPlan.addDish}
        </button>
        {entries.length > 0 && (
          <button type="button" className="btn btn-danger btn-block" onClick={handleClear}>
            {zh.picker.clearSlot}
          </button>
        )}
      </div>
    </div>
  );
}
