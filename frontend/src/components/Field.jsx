import { useId } from "react";
import { DateFilterInput } from "./DateFilterInput.jsx";
export function Field({ label, hint, children, as = "input", options, ...props }) {
  const id = useId();
  const Control = as;
  const attributes = { id, "aria-describedby": hint ? `${id}-hint` : undefined, ...props };
  const isFormattedDate =
    as === "input" &&
    props.type === "date" &&
    ["tu_ngay", "den_ngay", "han_hoan_thanh", "ngay_nhap"].includes(props.name);
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
      {isFormattedDate ? (
        <DateFilterInput {...attributes} label={label} />
      ) : as === "input" ? (
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
