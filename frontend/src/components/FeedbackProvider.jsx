import { createContext, useContext, useEffect, useRef, useState } from "react";
import { Button } from "./Button.jsx";
import { ErrorNotice } from "./QueryState.jsx";
import { Field } from "./Field.jsx";
const FeedbackContext = createContext(null);
export const useFeedback = () => useContext(FeedbackContext);

export function FeedbackProvider({ children }) {
  const [confirmation, setConfirmation] = useState(null);
  const [notice, setNotice] = useState("");
  const confirm = (options) => setConfirmation({ ...options, trigger: document.activeElement });
  return (
    <FeedbackContext.Provider
      value={{ confirm, notify: setNotice, dismissConfirmation: () => setConfirmation(null) }}
    >
      {children}
      {notice && (
        <div className="toast" role="status">
          <span>{notice}</span>
          <button type="button" aria-label="Đóng thông báo" onClick={() => setNotice("")}>
            ×
          </button>
        </div>
      )}
      {confirmation && (
        <Confirmation
          key={confirmation.title}
          options={confirmation}
          onClose={() => setConfirmation(null)}
        />
      )}
    </FeedbackContext.Provider>
  );
}

function Confirmation({ options, onClose }) {
  const dialog = useRef(null);
  const inFlight = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [reason, setReason] = useState("");
  useEffect(() => {
    const element = dialog.current;
    element.showModal();
    return () => {
      element.close();
      if (options.trigger?.isConnected) options.trigger.focus({ preventScroll: true });
    };
  }, []);
  async function submit(event) {
    event.preventDefault();
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await options.onConfirm(reason.trim());
      onClose();
    } catch (failure) {
      setError(failure);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className={`confirmation ${options.variant ? `confirmation-${options.variant}` : ""}`.trim()}
      aria-labelledby="confirmation-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <form onSubmit={submit}>
        <div className="dialog-header">
          <h2 id="confirmation-title">{options.title}</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Đóng xác nhận"
            disabled={busy}
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <div className="dialog-body stack">
          <p>{options.description}</p>
          {options.content}
          {!options.hideImpact && (
            <div className={`notice ${options.danger ? "notice-warning" : "notice-info"}`}>
              {options.impact || "Thao tác này không thay đổi tồn kho."}
            </div>
          )}
          {options.reason && (
            <Field
              as="textarea"
              rows={3}
              label={options.reasonLabel || "Lý do"}
              required
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              autoFocus
            />
          )}
          <ErrorNotice error={error} onNavigate={onClose} />
        </div>
        <div className="dialog-footer actions">
          <Button variant="secondary" onClick={onClose} disabled={busy}>
            Hủy
          </Button>
          <Button
            type="submit"
            variant={options.danger ? "danger" : "primary"}
            disabled={busy || Boolean(options.reason && !reason.trim())}
          >
            {busy ? "Đang xử lý…" : options.label || "Xác nhận"}
          </Button>
        </div>
      </form>
    </dialog>
  );
}
