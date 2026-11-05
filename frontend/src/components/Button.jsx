export function Button({
  variant = "primary",
  icon,
  children,
  className = "",
  reason,
  disabled,
  type = "button",
  ...props
}) {
  return (
    <span className="button-wrap">
      <button
        type={type}
        className={`btn btn-${variant} ${className}`}
        disabled={disabled || Boolean(reason)}
        aria-describedby={reason ? undefined : props["aria-describedby"]}
        title={reason}
        {...props}
      >
        {icon}
        {children}
      </button>
      {reason && <span className="disabled-reason">{reason}</span>}
    </span>
  );
}
