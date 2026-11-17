export function PageHeader({ title, subtitle, action, variant = "default" }) {
  if (variant === "large") {
    return (
      <div className="admin-page-heading">
        <h1>{title}</h1>
        {action && <div className="actions">{action}</div>}
      </div>
    );
  }
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      <div className="actions">{action}</div>
    </div>
  );
}
