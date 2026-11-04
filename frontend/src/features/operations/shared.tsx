import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { Button } from "@/components/Button";
import { X } from "lucide-react";
import { initial, label, type Database, type Role } from "./model";

const storageKey = "xbike-react-demo-v1";
function readSession(): { db: Database; role: Role; warning: string } {
  try {
    const stored = sessionStorage.getItem(storageKey);
    // Keep the versioned fixture shape intact; malformed or obsolete sessions are reset visibly.
    const saved = stored ? JSON.parse(stored) : null;
    if (
      saved &&
      (saved.version !== 1 ||
        !saved.db ||
        !Array.isArray(saved.db.items) ||
        !Array.isArray(saved.db.ledger) ||
        !Array.isArray(saved.db.orders) ||
        !Array.isArray(saved.db.adjustments) ||
        !Array.isArray(saved.db.tickets) ||
        !saved.db.names ||
        !Number.isInteger(saved.db.nextAdjustmentId) ||
        !Number.isInteger(saved.db.nextTicketId))
    )
      throw new Error("Invalid session");
    return {
      db: saved?.db || structuredClone(initial),
      role: ["Q", "N", "A"].includes(saved?.role) ? saved.role : "Q",
      warning: "",
    };
  } catch {
    return {
      db: structuredClone(initial),
      role: "Q",
      warning: "Không đọc được phiên demo. Đang dùng dữ liệu mẫu; dữ liệu cũ không được phục hồi.",
    };
  }
}
interface Demo {
  db: Database;
  role: Role;
  setRole: (role: Role) => void;
  notice: string;
  warning: string;
  mutate: (update: (db: Database) => string | void) => void;
  reset: () => void;
}
const DemoContext = createContext<Demo | null>(null);
export function DemoProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState(readSession);
  const [notice, setNotice] = useState("");
  const current = useRef(session.db);
  const { db, role, warning } = session;
  useEffect(() => {
    try {
      sessionStorage.setItem(storageKey, JSON.stringify({ version: 1, db, role }));
    } catch {
      setSession((s) =>
        s.warning
          ? s
          : { ...s, warning: "Không lưu được phiên demo. Thay đổi chỉ giữ đến khi tải lại trang." },
      );
    }
  }, [db, role]);
  const mutate: Demo["mutate"] = (update) => {
    const next = structuredClone(current.current);
    const message = update(next);
    current.current = next;
    setSession((s) => ({ ...s, db: next }));
    setNotice(message || "Đã lưu thay đổi trong dữ liệu demo.");
  };
  return (
    <DemoContext.Provider
      value={{
        db,
        role,
        warning,
        notice,
        mutate,
        setRole: (next) => setSession((s) => ({ ...s, role: next })),
        reset: () => {
          const next = structuredClone(initial);
          current.current = next;
          setSession((s) => ({ ...s, db: next }));
          setNotice("Đã khôi phục dữ liệu mẫu.");
        },
      }}
    >
      {children}
    </DemoContext.Provider>
  );
}
export function useDemo() {
  const context = useContext(DemoContext);
  if (!context) throw new Error("Missing demo provider");
  return context;
}
export function Status({ value }: { value: string }) {
  const tone = ["active", "hoan_thanh", "da_xac_nhan"].includes(value)
    ? "good"
    : value === "loi"
      ? "bad"
      : value === "da_gui"
        ? "warning"
        : "neutral";
  return <span className={`op-status ${tone}`}>{label(value)}</span>;
}
export function Notice({ children, tone = "" }: { children: ReactNode; tone?: string }) {
  return <div className={`op-notice ${tone}`}>{children}</div>;
}
export function Field({
  label: title,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="op-field">
      <span>{title}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Details({ values }: { values: [string, ReactNode][] }) {
  return (
    <dl className="op-details">
      {values.map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
export function Modal({
  title,
  children,
  onClose,
  onSubmit,
  submitLabel,
  conflict = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  onSubmit?: (data: FormData) => void;
  submitLabel?: string;
  conflict?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const submitting = useRef(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const dialog = ref.current!;
    const trigger = document.activeElement as HTMLElement;
    dialog.showModal();
    return () => {
      dialog.close();
      if (trigger?.isConnected) trigger.focus();
    };
  }, []);
  useEffect(() => {
    if (error) errorRef.current?.focus();
  }, [error]);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!onSubmit || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    try {
      if (conflict)
        throw new Error(
          "412 · Dữ liệu đã thay đổi. Đóng hộp thoại, tải lại danh sách và kiểm tra trước khi lưu.",
        );
      onSubmit(new FormData(event.currentTarget));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không lưu được. Vui lòng kiểm tra lại.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };
  return (
    <dialog
      className="op-dialog"
      ref={ref}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      aria-labelledby="op-dialog-title"
    >
      <form onSubmit={submit}>
        <header>
          <h2 id="op-dialog-title">{title}</h2>
          <button type="button" className="op-icon" onClick={onClose} aria-label="Đóng hộp thoại">
            <X size={20} />
          </button>
        </header>
        <div className="op-dialog-body">
          {error && (
            <p className="op-error" role="alert" ref={errorRef} tabIndex={-1}>
              {error}
            </p>
          )}
          {children}
        </div>
        <footer>
          <Button type="button" variant="secondary" onClick={onClose}>
            Đóng
          </Button>
          {onSubmit && (
            <Button type="submit" disabled={busy}>
              {busy ? "Đang lưu…" : submitLabel || "Lưu thay đổi"}
            </Button>
          )}
        </footer>
      </form>
    </dialog>
  );
}
export function Table({
  headers,
  children,
  label: title = "Bảng dữ liệu",
}: {
  headers: string[];
  children: ReactNode;
  label?: string;
}) {
  return (
    <div
      className="op-table-scroll"
      role="region"
      tabIndex={0}
      aria-label={`${title}, có thể cuộn ngang`}
    >
      <table>
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th
                key={index}
                scope="col"
                className={
                  [
                    "Đơn giá (₫)",
                    "Tồn hiện tại",
                    "Đầu ra đã duyệt",
                    "Biến động",
                    "Cần",
                    "Đã cấp",
                    "Còn cấp",
                    "Tồn kho",
                    "Hiệu lực trước",
                    "Số lượng đúng",
                    "Chênh lệch",
                    "Tồn sau",
                    "Hiệu lực",
                    "Tồn trước → sau",
                  ].includes(header)
                    ? "op-num"
                    : undefined
                }
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
