import { useEffect, useRef, useState } from "react";
import { Calendar } from "lucide-react";
import { dmyToIso, isoToDmy, maskDmy } from "../lib/dateInput.js";

export function DateInput({ value, onChange, id, name, shortYear = false, children: _children, ...rest }) {
  const [display, setDisplay] = useState(() => isoToDmy(value, shortYear));
  const [invalid, setInvalid] = useState(false);
  const textRef = useRef(null);
  const pickerRef = useRef(null);

  useEffect(() => {
    setDisplay(isoToDmy(value, shortYear));
    setInvalid(false);
    textRef.current?.setCustomValidity("");
  }, [value, shortYear]);

  function changeDisplay(text) {
    const masked = maskDmy(text, shortYear);
    const iso = dmyToIso(masked, shortYear);
    const isInvalid = masked !== "" && iso === null;
    setDisplay(masked);
    setInvalid(isInvalid);
    const formatNotice = shortYear ? "Nhập ngày theo dd/mm/yy." : "Nhập ngày theo dd/mm/yyyy.";
    textRef.current.setCustomValidity(isInvalid ? formatNotice : "");
    if (!isInvalid) onChange?.({ target: { value: iso ?? "" } });
  }

  function handlePickerChange(event) {
    const iso = event.target.value;
    setDisplay(isoToDmy(iso, shortYear));
    setInvalid(false);
    textRef.current?.setCustomValidity("");
    onChange?.({ target: { value: iso || "" } });
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
        placeholder={shortYear ? "dd/mm/yy" : "dd/mm/yyyy"}
        maxLength={shortYear ? 8 : 10}
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
        onChange={handlePickerChange}
      />
    </div>
  );
}
