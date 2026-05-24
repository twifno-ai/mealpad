import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  addDays,
  api,
  formatIsoDate,
  mondayOfWeek,
  type CookedDishLog,
} from "../api";
import { formatDayHeader } from "../locale/format";
import { slotLabel, zh } from "../locale/zh";

const SLOTS = ["lunch", "dinner"] as const;

export default function JournalPage() {
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

  const [logs, setLogs] = useState<CookedDishLog[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setLogs(await api.getCookedDishes(startIso, endIso));
    } catch (e) {
      console.error(e);
      setError(zh.error.loadFailed);
    } finally {
      setLoading(false);
    }
  }, [startIso, endIso]);

  useEffect(() => {
    load();
  }, [load]);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  function goWeek(offset: number) {
    navigate(`/journal/${formatIsoDate(addDays(weekStart, offset * 7))}`);
  }

  const hasAny = logs.length > 0;

  return (
    <div className="page">
      <header className="page-header">
        <h1>{zh.journal.title}</h1>
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

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">{zh.loading}</p>}

      {!loading && !hasAny && <p className="muted">{zh.journal.empty}</p>}

      {!loading &&
        days.map((day) => {
          const iso = formatIsoDate(day);
          const dayLogs = logs.filter((log) => log.date === iso);
          if (dayLogs.length === 0) return null;
          return (
            <section key={iso} className="day-card">
              <h2 className="day-title">{formatDayHeader(day)}</h2>
              {SLOTS.map((slot) => {
                const slotLogs = dayLogs.filter((log) => log.slot === slot);
                if (slotLogs.length === 0) return null;
                return (
                  <div key={slot} className="journal-slot">
                    <h3 className="journal-slot-title">{slotLabel(slot)}</h3>
                    <ul className="list">
                      {slotLogs.map((log) => (
                        <li key={log.id} className="journal-log-row">
                          {log.photo_url && (
                            <button
                              type="button"
                              className="journal-thumb-btn"
                              onClick={() => window.open(log.photo_url!, "_blank")}
                            >
                              <img src={log.photo_url} alt="" className="cooked-thumb" />
                            </button>
                          )}
                          <div className="journal-log-text">
                            {log.recipe_id != null ? (
                              <Link to={`/recipes/${log.recipe_id}/edit`} className="list-row-title">
                                {log.recipe_name}
                              </Link>
                            ) : (
                              <span className="list-row-title">{log.recipe_name}</span>
                            )}
                            <span className="badge">
                              {log.kind === "planned" ? zh.cooked.planned : zh.cooked.extra}
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </section>
          );
        })}
    </div>
  );
}
