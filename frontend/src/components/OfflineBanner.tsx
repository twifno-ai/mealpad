import { useConnection } from "../context/ConnectionContext";
import { zh } from "../locale/zh";

export default function OfflineBanner() {
  const { online } = useConnection();
  if (online) return null;
  return <div className="offline-banner">{zh.connection.offline}</div>;
}
