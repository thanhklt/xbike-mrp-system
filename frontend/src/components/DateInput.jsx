import { useEffect, useRef, useState } from "react";
import { Calendar } from "lucide-react";
import { dmyToIso, isoToDmy, maskDmy } from "../lib/dateInput.js";

export function DateInput({ value, onChange, id, name, children: _children, ...rest }) {
  const [display, setDisplay] = useState(() => isoToDmy(value));
  const [invalid, setInvalid] = useState(false);
  const textRef = useRef(null);
  const pickerRef = useRef(null);

  useEffect(() => {
    setDisplay(isoToDmy(value));
    setInvalid(false);
    textRef.current?.setCustomValidity("");
  }, [value]);

  function changeDisplay(text) {
    const masked = maskDmy(text);
    const iso = dmyToIso(masked);
    const isInvalid = masked !== "" && iso === null;
    setDisplay(masked);
    setInvalid(isInvalid);
    textRef.current.setCustomValidity(isInvalid ? "Nhập ngày theo dd/mm/yyyy." : "");
    if (!isInvalid) onChange?.({ target: { value: iso ?? "" } });
  }

  function openPicker() {
    if (pickerRef.current.showPicker) {
      try {
        pickerRef.current.showPicker();
        return;
      } catch {
        // Không mở được lịch thì tiếp tục nhập bằng bàn phím.
      }
    }
    textRef.current.focus();
  }

  return (
    <div className="date-input">
      <input
        {...rest}
        ref={textRef}
        id={id}
        name={name}
        type="text"
        inputMode="numeric"
        placeholder="dd/mm/yyyy"
        maxLength={10}
        value={display}
        aria-invalid={invalid || undefined}
        onChange={(event) => changeDisplay(event.target.value)}
      />
      <button type="button" aria-label="Chọn ngày" disabled={rest.disabled} onClick={openPicker}>
        <Calendar size={18} aria-hidden="true" />
      </button>
      <input
        ref={pickerRef}
        className="date-input-picker"
        type="date"
        tabIndex={-1}
        aria-hidden="true"
        disabled={rest.disabled}
        value={value || ""}
        onChange={(event) => changeDisplay(isoToDmy(event.target.value))}
      />
    </div>
  );
}
