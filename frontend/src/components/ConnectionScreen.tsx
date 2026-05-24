import { useState } from "react";
import { useConnection } from "../context/ConnectionContext";
import { zh } from "../locale/zh";

export default function ConnectionScreen() {
  const { retry, status } = useConnection();
  const [showHelp, setShowHelp] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copyOrigin() {
    await navigator.clipboard.writeText(window.location.origin);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="connection-screen">
      <h1>{zh.connection.title}</h1>
      <p>{zh.connection.hint}</p>
      <ul className="connection-checklist">
        <li>{zh.connection.checkServe}</li>
        <li>{zh.connection.checkIp}</li>
      </ul>
      <button
        type="button"
        className="btn btn-primary btn-block"
        onClick={retry}
        disabled={status === "checking"}
      >
        {status === "checking" ? zh.loading : zh.connection.retry}
      </button>
      <button type="button" className="btn btn-secondary btn-block" onClick={copyOrigin}>
        {copied ? zh.connection.copied : zh.connection.copyAddress}
      </button>
      <button
        type="button"
        className="btn btn-secondary btn-block"
        onClick={() => setShowHelp((v) => !v)}
      >
        {zh.connection.helpTitle}
      </button>
      {showHelp && <pre className="connection-help">{zh.connection.helpBody}</pre>}
    </div>
  );
}
