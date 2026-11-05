import { Link } from "react-router-dom";
import { Card } from "./Card.jsx";
import { Button } from "./Button.jsx";
import { QueryState } from "./QueryState.jsx";
export function RecordPanel({ id, query, title, base, children }) {
  if (!id) return null;
  return (
    <Card
      className="record-panel"
      title={title}
      action={
        <div className="actions">
          {id !== "moi" && (
            <Button variant="secondary" onClick={() => query.refetch()} disabled={query.isFetching}>
              Tải lại chi tiết
            </Button>
          )}
          <Link to={base} className="text-link">
            Đóng
          </Link>
        </div>
      }
    >
      {id === "moi" ? (
        children(null)
      ) : (
        <QueryState query={query}>
          {query.data && (
            <div key={`${id}-${query.data.etag || "read"}`}>{children(query.data)}</div>
          )}
        </QueryState>
      )}
    </Card>
  );
}
export function InfoGrid({ entries }) {
  return (
    <dl className="info-grid">
      {entries.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value ?? "—"}</dd>
        </div>
      ))}
    </dl>
  );
}
