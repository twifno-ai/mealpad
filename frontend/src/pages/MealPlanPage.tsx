import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import MealSlotModal from "../components/MealSlotModal";
import RecipePicker from "../components/RecipePicker";
import { getErrorMessage } from "../httpErrors";
import {
  addDays,
  api,
  formatIsoDate,
  mondayOfWeek,
  type MealPlanEntry,
} from "../api";
import { formatDayHeader } from "../locale/format";
import { slotLabel, zh } from "../locale/zh";

const SLOTS = ["lunch", "dinner"] as const;

type PickerState = {
  date: string;
  slot: string;
  mode: "add" | "replace";
  entryId?: number;
};

type MealModalState = {
  date: string;
  slot: string;
};

function mealKey(date: string, slot: string) {
  return `${date}:${slot}`;
}

function formatMealSummary(entries: MealPlanEntry[]) {
  if (entries.length === 0) return zh.mealPlan.addSlot;
  return entries.map((e) => e.recipe.name).join(" · ");
}

export default function MealPlanPage() {
  const { weekStart: weekStartParam } = useParams();
  const navigate = useNavigate();
  const weekStart = useMemo(() => {
    if (weekStartParam) {
      const d = new Date(`${weekStartParam}T12:00:00`);
      if (!Number.isNaN(d.getTime())) return mondayOfWeek(d);
    }
    return mondayOfWeek(new Date());
  }, [weekStartParam]);

  const weekEnd = useMemo(() => addDays(weekStart, 6), [weekStart]);
  const startIso = formatIsoDate(weekStart);
  const endIso = formatIsoDate(weekEnd);

  const [entries, setEntries] = useState<MealPlanEntry[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [mealModal, setMealModal] = useState<MealModalState | null>(null);
  const [picker, setPicker] = useState<PickerState | null>(null);
  const [hasList, setHasList] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.getMealPlan(startIso, endIso);
      setEntries(data);
    } catch (e) {
      console.error(e);
      setError(zh.mealPlan.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [startIso, endIso]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api
      .getShoppingList(startIso, endIso)
      .then(() => setHasList(true))
      .catch(() => setHasList(false));
  }, [startIso, endIso]);

  const entriesByMeal = useMemo(() => {
    const map = new Map<string, MealPlanEntry[]>();
    for (const entry of entries) {
      const key = mealKey(entry.date, entry.slot);
      const list = map.get(key) ?? [];
      list.push(entry);
      map.set(key, list);
    }
    for (const list of map.values()) {
      list.sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
    }
    return map;
  }, [entries]);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  const emptyMeals = useMemo(() => {
    let count = 0;
    for (const day of days) {
      const iso = formatIsoDate(day);
      for (const slot of SLOTS) {
        if ((entriesByMeal.get(mealKey(iso, slot))?.length ?? 0) === 0) count += 1;
      }
    }
    return count;
  }, [days, entriesByMeal]);

  const modalEntries = useMemo(() => {
    if (!mealModal) return [];
    return entriesByMeal.get(mealKey(mealModal.date, mealModal.slot)) ?? [];
  }, [mealModal, entriesByMeal]);

  function goWeek(offset: number) {
    const next = addDays(weekStart, offset * 7);
    navigate(`/plan/${formatIsoDate(next)}`);
  }

  async function handleGenerate() {
    setGenerating(true);
    setError("");
    try {
      await api.generateMealPlan(startIso, endIso);
      await load();
    } catch (e) {
      console.error(e);
      setError(getErrorMessage(e, zh.mealPlan.aiFillFailed));
    } finally {
      setGenerating(false);
    }
  }

  async function handleRegenerate() {
    if (!confirm(zh.mealPlan.regenerateConfirm)) return;
    setRegenerating(true);
    setError("");
    try {
      await api.regenerateMealPlan(startIso, endIso);
      setHasList(false);
      await load();
    } catch (e) {
      console.error(e);
      setError(getErrorMessage(e, zh.mealPlan.regenerateFailed));
    } finally {
      setRegenerating(false);
    }
  }

  async function handleShoppingAction() {
    if (hasList) {
      navigate(`/plan/${startIso}/shopping`);
      return;
    }
    setError("");
    try {
      await api.generateShoppingList(startIso, endIso);
      navigate(`/plan/${startIso}/shopping`);
    } catch (e) {
      console.error(e);
      setError(getErrorMessage(e, zh.mealPlan.generateListFailed));
    }
  }

  async function handleRecipeSelected(recipeId: number) {
    if (!picker) return;
    if (picker.mode === "add") {
      await api.addMealPlanItem(picker.date, picker.slot, recipeId);
    } else if (picker.entryId != null) {
      await api.updateMealPlanItem(picker.entryId, recipeId);
    }
    setPicker(null);
    await load();
  }

  async function handleRemoveDish(entryId: number) {
    await api.deleteMealPlanItem(entryId);
    await load();
  }

  async function handleClearMeal() {
    if (!mealModal) return;
    await api.deleteMealPlanSlot(mealModal.date, mealModal.slot);
    setMealModal(null);
    await load();
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>{zh.mealPlan.title}</h1>
        <Link to="/recipes" className="btn btn-secondary">
          {zh.mealPlan.recipes}
        </Link>
      </header>

      <div className="toolbar week-nav">
        <button type="button" className="btn btn-secondary" onClick={() => goWeek(-1)}>
          ◀
        </button>
        <span className="week-label">
          {startIso} – {endIso}
        </span>
        <button type="button" className="btn btn-secondary" onClick={() => goWeek(1)}>
          ▶
        </button>
      </div>

      <div className="toolbar">
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleShoppingAction}
          disabled={hasList === null}
        >
          {hasList ? zh.mealPlan.viewList : zh.mealPlan.generateList}
        </button>
        {emptyMeals > 0 && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleGenerate}
            disabled={generating || regenerating}
          >
            {generating ? zh.mealPlan.filling : zh.mealPlan.autoFill}
          </button>
        )}
        {entries.length > 0 && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleRegenerate}
            disabled={generating || regenerating}
          >
            {regenerating ? zh.mealPlan.regenerating : zh.mealPlan.regenerate}
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">{zh.loading}</p>}

      {!loading &&
        days.map((day) => {
          const iso = formatIsoDate(day);
          return (
            <section key={iso} className="day-card">
              <h2 className="day-title">{formatDayHeader(day)}</h2>
              {SLOTS.map((slot) => {
                const mealEntries = entriesByMeal.get(mealKey(iso, slot)) ?? [];
                return (
                  <button
                    key={slot}
                    type="button"
                    className="slot-row"
                    onClick={() => setMealModal({ date: iso, slot })}
                  >
                    <span className="slot-label">{slotLabel(slot)}</span>
                    <span className="slot-value">{formatMealSummary(mealEntries)}</span>
                  </button>
                );
              })}
            </section>
          );
        })}

      {mealModal && (
        <MealSlotModal
          date={mealModal.date}
          slot={mealModal.slot}
          entries={modalEntries}
          onAdd={() => {
            setPicker({ date: mealModal.date, slot: mealModal.slot, mode: "add" });
          }}
          onReplace={(entryId) => {
            setPicker({
              date: mealModal.date,
              slot: mealModal.slot,
              mode: "replace",
              entryId,
            });
          }}
          onRemove={handleRemoveDish}
          onClearMeal={handleClearMeal}
          onClose={() => setMealModal(null)}
        />
      )}

      {picker && (
        <RecipePicker
          title={picker.mode === "add" ? zh.mealPlan.addDish : zh.mealPlan.replaceDish}
          showClear={false}
          onSelect={handleRecipeSelected}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  );
}
