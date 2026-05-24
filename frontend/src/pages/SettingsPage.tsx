import { Link } from "react-router-dom";
import { formatIsoDate, mondayOfWeek } from "../api";
import { useConnection } from "../context/ConnectionContext";
import { zh } from "../locale/zh";

export default function SettingsPage() {
  const { status, retry } = useConnection();
  const origin = window.location.origin;
  const week = formatIsoDate(mondayOfWeek(new Date()));

  async function copyOrigin() {
    await navigator.clipboard.writeText(origin);
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>{zh.settings.title}</h1>
        <Link to={`/plan/${week}`} className="btn btn-secondary">
          {zh.back}
        </Link>
      </header>
      <p className="muted">{zh.settings.serverAddress}</p>
      <p className="settings-origin">{origin}</p>
      <button type="button" className="btn btn-secondary btn-block" onClick={copyOrigin}>
        {zh.connection.copyAddress}
      </button>
      <button type="button" className="btn btn-primary btn-block" onClick={retry}>
        {zh.settings.checkConnection}
      </button>
      <p className="muted">
        {status === "ok"
          ? zh.settings.connected
          : status === "failed"
            ? zh.settings.failed
            : zh.loading}
      </p>
      <pre className="connection-help">{zh.connection.helpBody}</pre>
      <p className="muted">{zh.settings.backupHint}</p>
    </div>
  );
}
