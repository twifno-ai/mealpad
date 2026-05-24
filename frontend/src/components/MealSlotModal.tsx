import { useRef, useState } from "react";
import { type CookedDishLog, type MealPlanEntry } from "../api";
import { recipeTypeLabel, cuisineLabel, slotLabel, zh } from "../locale/zh";

interface Props {
  date: string;
  slot: string;
  entries: MealPlanEntry[];
  cookedLogs: CookedDishLog[];
  onAdd: () => void;
  onReplace: (entryId: number) => void;
  onRemove: (entryId: number) => Promise<void>;
  onClearMeal: () => Promise<void>;
  onMarkCooked: (entryId: number, photo?: File) => Promise<void>;
  onUnmarkCooked: (logId: number) => Promise<void>;
  onAddExtra: () => void;
  onClose: () => void;
}

export default function MealSlotModal({
  date,
  slot,
  entries,
  cookedLogs,
  onAdd,
  onReplace,
  onRemove,
  onClearMeal,
  onMarkCooked,
  onUnmarkCooked,
  onAddExtra,
  onClose,
}: Props) {
  const [error, setError] = useState("");
  const photoInputRef = useRef<HTMLInputElement>(null);
  const pendingEntryIdRef = useRef<number | null>(null);

  const extraLogs = cookedLogs.filter((log) => log.kind === "extra");

  function cookedForEntry(entryId: number) {
    return cookedLogs.find((log) => log.meal_plan_entry_id === entryId);
  }

  function openPhotoPicker(entryId: number) {
    pendingEntryIdRef.current = entryId;
    photoInputRef.current?.click();
  }

  async function handlePhotoSelected(file: File | undefined) {
    const entryId = pendingEntryIdRef.current;
    pendingEntryIdRef.current = null;
    if (entryId == null || !file) return;
    setError("");
    try {
      await onMarkCooked(entryId, file);
    } catch (e) {
      console.error(e);
      setError(zh.error.generic);
    }
  }

  async function handleMark(entryId: number) {
    setError("");
    try {
      await onMarkCooked(entryId);
    } catch (e) {
      console.error(e);
      setError(zh.error.generic);
    }
  }

  async function handleUnmark(logId: number) {
    setError("");
    try {
      await onUnmarkCooked(logId);
    } catch (e) {
      console.error(e);
      setError(zh.error.generic);
    }
  }

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
      <input
        ref={photoInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="visually-hidden"
        onChange={(e) => {
          handlePhotoSelected(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
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

        <h3 className="meal-section-title">{zh.cooked.sectionPlanned}</h3>
        {entries.length === 0 ? (
          <p className="muted">{zh.mealPlan.emptyMeal}</p>
        ) : (
          <ul className="list meal-dish-list">
            {entries.map((entry) => {
              const cooked = cookedForEntry(entry.id);
              return (
                <li key={entry.id} className="meal-dish-row">
                  <div className="meal-dish-info">
                    <span className="list-row-title">{entry.recipe.name}</span>
                    <span className="list-row-sub">
                      {cuisineLabel(entry.recipe.cuisine)} · {recipeTypeLabel(entry.recipe.type)}
                    </span>
                    {cooked && (
                      <div className="cooked-row-meta">
                        <span className="badge badge-done">✓ {zh.cooked.planned}</span>
                        {cooked.photo_url && (
                          <img
                            src={cooked.photo_url}
                            alt=""
                            className="cooked-thumb"
                            onClick={() => window.open(cooked.photo_url!, "_blank")}
                          />
                        )}
                      </div>
                    )}
                  </div>
                  <div className="meal-dish-actions">
                    {cooked ? (
                      <button
                        type="button"
                        className="btn btn-secondary btn-icon"
                        onClick={() => handleUnmark(cooked.id)}
                      >
                        {zh.cooked.unmark}
                      </button>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn btn-primary btn-icon"
                          onClick={() => handleMark(entry.id)}
                        >
                          {zh.cooked.markDone}
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-icon"
                          onClick={() => openPhotoPicker(entry.id)}
                        >
                          {zh.cooked.markWithPhoto}
                        </button>
                      </>
                    )}
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
              );
            })}
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

        <h3 className="meal-section-title">{zh.cooked.sectionActual}</h3>
        {extraLogs.length === 0 ? (
          <p className="muted">{zh.cooked.addExtra}</p>
        ) : (
          <ul className="list meal-dish-list">
            {extraLogs.map((log) => (
              <li key={log.id} className="meal-dish-row">
                <div className="meal-dish-info">
                  <span className="list-row-title">{log.recipe_name}</span>
                  <span className="badge">{zh.cooked.extra}</span>
                  {log.photo_url && (
                    <img
                      src={log.photo_url}
                      alt=""
                      className="cooked-thumb"
                      onClick={() => window.open(log.photo_url!, "_blank")}
                    />
                  )}
                </div>
                <button
                  type="button"
                  className="btn btn-danger btn-icon"
                  onClick={() => handleUnmark(log.id)}
                >
                  {zh.cooked.unmark}
                </button>
              </li>
            ))}
          </ul>
        )}
        <button type="button" className="btn btn-secondary btn-block" onClick={onAddExtra}>
          {zh.cooked.addExtra}
        </button>
      </div>
    </div>
  );
}
