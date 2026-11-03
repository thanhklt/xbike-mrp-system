import { useEffect, useId, useRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { AlertCircle, ArrowRight, Check, Info, X } from "lucide-react";
import { itemById, number } from "./planning";
import type { Item, MaterialDemand } from "./types";

export function ActionButton({
  children,
  variant = "secondary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "plain";
}) {
  return (
    <button type="button" className={`m-button m-button--${variant} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function PageTitle({
  title,
  description,
  step,
  action,
}: {
  title: string;
  description: string;
  step: string;
  action?: ReactNode;
}) {
  return (
    <div className="m-page-title">
      <div>
        <div className="m-page-context">
          Nghiệp vụ quản lý <span>/</span> {step}
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`m-panel ${className}`}>
      <header className="m-panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </header>
      {children}
    </section>
  );
}

export function Field({
  label,
  required,
  hint,
  children,
  wide,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <label className={`m-field ${wide ? "m-field--wide" : ""}`}>
      <span className="m-field-label">
        {label}
        {required && <span className="m-required"> *</span>}
      </span>
      {children}
      {hint && <span className="m-help">{hint}</span>}
    </label>
  );
}

export function Status({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "green" | "amber" | "red";
}) {
  return (
    <span className={`m-status m-status--${tone}`}>
      <span aria-hidden="true" />
      {children}
    </span>
  );
}

export function Notice({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "green" | "amber";
}) {
  const Icon = tone === "green" ? Check : tone === "amber" ? AlertCircle : Info;
  return (
    <div className={`m-notice m-notice--${tone}`}>
      <Icon size={17} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}

export function FormError({ error }: { error: Error | null }) {
  return error ? (
    <div className="m-form-error" role="alert">
      <AlertCircle size={17} aria-hidden="true" />
      {error.message}
    </div>
  ) : null;
}

export function ConfirmDialog({
  title,
  children,
  confirmLabel,
  danger,
  busy,
  onConfirm,
  onClose,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  danger?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      className="m-dialog"
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <div className="m-dialog-heading">
        <h2 id={titleId}>{title}</h2>
        <ActionButton variant="plain" aria-label="Đóng hộp thoại" onClick={onClose} disabled={busy}>
          <X size={19} />
        </ActionButton>
      </div>
      <div className="m-dialog-content">{children}</div>
      <footer>
        <ActionButton onClick={onClose} disabled={busy}>
          Quay lại
        </ActionButton>
        <ActionButton variant={danger ? "danger" : "primary"} disabled={busy} onClick={onConfirm}>
          {busy ? "Đang xử lý…" : confirmLabel}
          <ArrowRight size={16} />
        </ActionButton>
      </footer>
    </dialog>
  );
}

export function MaterialTable({
  lines,
  items,
  label = "Theo BOM đã chọn",
}: {
  lines: readonly MaterialDemand[];
  items: readonly Item[];
  label?: string;
}) {
  return (
    <div className="m-table-scroll">
      <table className="m-table">
        <caption className="m-sr-only">{label}</caption>
        <thead>
          <tr>
            <th>Vật tư / Bán thành phẩm</th>
            <th className="m-number">Định mức</th>
            <th className="m-number">Nhu cầu</th>
            <th className="m-number">Tồn hiện tại</th>
            <th>Khả dụng</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => {
            const item = itemById(items, line.itemId);
            return (
              <tr key={line.itemId}>
                <td>
                  <strong>{item.name}</strong>
                  <small>
                    {item.code} · {item.unit}
                  </small>
                </td>
                <td className="m-number">{number(line.perUnit)}</td>
                <td className="m-number">
                  <strong>{number(line.required)}</strong>
                </td>
                <td className="m-number">{number(line.available)}</td>
                <td>
                  {line.missing > 0 ? (
                    <Status tone="amber">Thiếu {number(line.missing)}</Status>
                  ) : (
                    <Status tone="green">Đủ vật tư</Status>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
