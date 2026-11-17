import { RotateCw } from "lucide-react";

export function CycleButton({ id, name, value = "", options = [], onChange, disabled, "aria-labelledby": labelId }) {
  const index = options.findIndex((option) => String(option.value) === String(value));
  const selected = options[index] || options[0];
  return (
    <div className="button-dropdown">
      <input type="hidden" name={name} value={value} />
      <button
        id={id}
        type="button"
        className="btn-dropdown-trigger"
        aria-labelledby={`${labelId} ${id}-value`}
        title="Bấm để chuyển sang lựa chọn tiếp theo"
        disabled={disabled || options.length < 2}
        onClick={() => onChange({ target: { name, value: options[(index + 1) % options.length].value } })}
      >
        <span id={`${id}-value`} className="btn-dropdown-label">{selected?.label}</span>
        <RotateCw size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
