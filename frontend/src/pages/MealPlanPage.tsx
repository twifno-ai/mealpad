import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
  const [picker, setPicker] = useState<{ date: string; slot: string } | null>(null);
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

  const entryMap = useMemo(() => {
    const map = new Map<string, MealPlanEntry>();
    for (const e of entries) {
      map.set(`${e.date}:${e.slot}`, e);
    }
    return map;
  }, [entries]);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  const emptySlots = useMemo(() => {
    let count = 0;
    for (const day of days) {
      const iso = formatIsoDate(day);
      for (const slot of SLOTS) {
        if (!entryMap.has(`${iso}:${slot}`)) count += 1;
      }
    }
    return count;
  }, [days, entryMap]);

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

  async function assignRecipe(recipeId: number) {
    if (!picker) return;
    await api.upsertMealPlanEntry(picker.date, picker.slot, recipeId);
    setPicker(null);
    await load();
  }

  async function clearSlot() {
    if (!picker) return;
    await api.deleteMealPlanEntry(picker.date, picker.slot);
    setPicker(null);
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
        {emptySlots > 0 && (
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
                const entry = entryMap.get(`${iso}:${slot}`);
                return (
                  <button
                    key={slot}
                    type="button"
                    className="slot-row"
                    onClick={() => setPicker({ date: iso, slot })}
                  >
                    <span className="slot-label">{slotLabel(slot)}</span>
                    <span className="slot-value">
                      {entry ? entry.recipe.name : zh.mealPlan.addSlot}
                    </span>
                  </button>
                );
              })}
            </section>
          );
        })}

      {picker && (
        <RecipePicker
          onSelect={assignRecipe}
          onClear={clearSlot}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  );
}
