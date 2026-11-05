import { useEffect, useId, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "./Button.jsx";
import { QueryState } from "./QueryState.jsx";
export function RecordPanel({ id, query, title, base, children }) {
  if (!id) return null;
  return (
    <RecordDialog key={id} id={id} query={query} title={title} base={base}>
      {children}
    </RecordDialog>
  );
}

function RecordDialog({ id, query, title, base, children }) {
  const dialog = useRef(null);
  const titleId = useId();
  const navigate = useNavigate();
  useEffect(() => {
    const element = dialog.current;
    const trigger = document.activeElement;
    element.showModal();
    return () => {
      element.close();
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, []);
  function close() {
    navigate(base);
  }
  function trapFocus(event) {
    if (event.key !== "Tab") return;
    const controls = [
      ...event.currentTarget.querySelectorAll(
        'a[href], button:not(:disabled), input:not(:disabled):not([type="hidden"]), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ),
    ].filter((element) => element.getClientRects().length > 0);
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  return (
    <dialog
      ref={dialog}
      className="record-dialog"
      aria-labelledby={titleId}
      onKeyDown={trapFocus}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <div className="dialog-header">
        <h2 id={titleId}>{title}</h2>
        <div className="actions">
          {id !== "moi" && (
            <Button variant="secondary" onClick={() => query.refetch()} disabled={query.isFetching}>
              Tải lại chi tiết
            </Button>
          )}
          <Button variant="secondary" onClick={close} autoFocus>
            Đóng
          </Button>
        </div>
      </div>
      <div className="dialog-body">
        {id === "moi" ? (
          children(null)
        ) : (
          <QueryState query={query}>
            {query.data && (
              <div key={`${id}-${query.data.etag || "read"}`}>{children(query.data)}</div>
            )}
          </QueryState>
        )}
      </div>
    </dialog>
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
