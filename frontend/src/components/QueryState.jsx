import { Link } from "react-router-dom";
import { Button } from "./Button.jsx";
export function ErrorNotice({ error, onNavigate }) {
  if (!error) return null;
  return (
    <div className="notice notice-error" role="alert">
      <strong>{error.message || "Không thể tải dữ liệu."}</strong>
      {[412, 428].includes(error.status) && (
        <p>
          Tải lại chi tiết, kiểm tra nội dung rồi xác nhận lại. Các thay đổi chưa lưu có thể mất khi
          tải lại.
        </p>
      )}
      {error.details?.length > 0 && (
        <ul>
          {error.details.map((entry, index) => (
            <li key={index}>
              {entry.field || (entry.mat_hang_id && `Mặt hàng #${entry.mat_hang_id}`) || "Chi tiết"}
              : {entry.reason || JSON.stringify(entry)}
            </li>
          ))}
        </ul>
      )}
      {error.ticketId && (
        <p>
          Đã lưu ticket{" "}
          <Link to={`/kho/ticket/${error.ticketId}`} onClick={onNavigate}>
            #{error.ticketId}
          </Link>
          .
        </p>
      )}
      {error.requestId && <small>Mã yêu cầu: {error.requestId}</small>}
    </div>
  );
}
export function QueryState({ query, children }) {
  if (query.isPending)
    return (
      <div className="loading" role="status">
        <span className="spinner" /> Đang tải dữ liệu…
      </div>
    );
  if (query.isError)
    return (
      <div className="stack">
        <ErrorNotice error={query.error} />
        <Button variant="secondary" onClick={() => query.refetch()}>
          Tải lại
        </Button>
      </div>
    );
  return children;
}
export function Notice({ children, tone = "info" }) {
  return <div className={`notice notice-${tone}`}>{children}</div>;
}
