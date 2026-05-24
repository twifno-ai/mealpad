import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getErrorMessage } from "../httpErrors";
import { addDays, api, formatIsoDate, mondayOfWeek, type ShoppingList } from "../api";
import { categoryLabel, zh } from "../locale/zh";

const CATEGORY_ORDER = [
  "produce",
  "meat",
  "dairy",
  "bakery",
  "frozen",
  "pantry",
  "other",
];

export default function ShoppingListPage() {
  const navigate = useNavigate();
  const { weekStart: weekStartParam } = useParams();
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

  const [list, setList] = useState<ShoppingList | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setList(await api.getShoppingList(startIso, endIso));
    } catch (e) {
      console.error(e);
      setError(zh.shopping.empty);
      setList(null);
    } finally {
      setLoading(false);
    }
  }, [startIso, endIso]);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleItem(id: number, checked: boolean) {
    const updated = await api.toggleShoppingItem(id, !checked);
    setList((prev) => {
      if (!prev) return prev;
      const items_by_category = { ...prev.items_by_category };
      for (const cat of Object.keys(items_by_category)) {
        items_by_category[cat] = items_by_category[cat].map((item) =>
          item.id === id ? { ...item, checked: updated.checked } : item,
        );
      }
      return { ...prev, items_by_category };
    });
  }

  function goWeek(offset: number) {
    navigate(`/shopping/${formatIsoDate(addDays(weekStart, offset * 7))}`);
  }

  async function handleRegenerate() {
    if (!confirm(zh.shopping.regenerateConfirm)) return;
    setRegenerating(true);
    setError("");
    try {
      setList(await api.generateShoppingList(startIso, endIso));
    } catch (e) {
      console.error(e);
      setError(getErrorMessage(e, zh.shopping.regenerateFailed));
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>{zh.shopping.title}</h1>
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

      {error && !list && !loading && (
        <p className="muted">
          {zh.shopping.empty}{" "}
          <Link to={`/plan/${startIso}`}>{zh.shopping.goToPlan}</Link>
        </p>
      )}
      {loading && <p className="muted">{zh.loading}</p>}

      {list &&
        CATEGORY_ORDER.map((category) => {
          const items = list.items_by_category[category] ?? [];
          if (items.length === 0) return null;
          return (
            <section key={category} className="card-section">
              <h2 className="section-title">{categoryLabel(category)}</h2>
              <ul className="list">
                {items.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={`check-row ${item.checked ? "checked" : ""}`}
                      onClick={() => toggleItem(item.id, item.checked)}
                    >
                      <span className="checkbox" aria-hidden>
                        {item.checked ? "✓" : ""}
                      </span>
                      <span className="check-text">{item.text}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}

      {list && (
        <button
          type="button"
          className="btn btn-danger btn-block"
          onClick={handleRegenerate}
          disabled={regenerating}
        >
          {regenerating ? zh.shopping.regenerating : zh.shopping.regenerate}
        </button>
      )}
    </div>
  );
}
