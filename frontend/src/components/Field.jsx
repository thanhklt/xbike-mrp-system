import { useId } from "react";
export function Field({ label, hint, children, as = "input", options, ...props }) {
  const id = useId();
  const Control = as;
  const attributes = { id, "aria-describedby": hint ? `${id}-hint` : undefined, ...props };
  return (
    <div className="field">
      <div className="field-label">
        <label htmlFor={id}>{label}</label>
        {props.required && (
          <span className="required" aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </div>
      {as === "input" ? (
        <input {...attributes} />
      ) : (
        <Control {...attributes}>
          {options?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
          {children}
        </Control>
      )}
      {hint && (
        <small id={`${id}-hint`} className="muted">
          {hint}
        </small>
      )}
    </div>
  );
}
