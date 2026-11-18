import { useEffect, useRef } from "react";
import { CalendarDays } from "lucide-react";
import { dateFilterDisplayValue, dateFilterIsoValue } from "./dateFilterValue.js";
import styles from "./DateFilterInput.module.css";

export function DateFilterInput({ label, value = "", onChange, name, ...props }) {
  const textInput = useRef(null);
  const picker = useRef(null);
  const isoValue = dateFilterIsoValue(value);
  useEffect(() => {
    textInput.current.setCustomValidity(
      isoValue === null ? "Nhập ngày hợp lệ theo định dạng dd/mm/yyyy." : "",
    );
  }, [isoValue]);

  function change(nextValue) {
    onChange?.({ target: { name, value: dateFilterIsoValue(nextValue) ?? nextValue } });
  }

  function openPicker() {
    if (typeof picker.current.showPicker === "function") picker.current.showPicker();
    else {
      picker.current.focus();
      picker.current.click();
    }
  }

  return (
    <div className={styles.control}>
      <input
        {...props}
        ref={textInput}
        className={styles.textInput}
        name={name}
        type="text"
        value={dateFilterDisplayValue(value)}
        placeholder="dd/mm/yyyy"
        maxLength={10}
        pattern="[0-9]{2}/[0-9]{2}/[0-9]{4}"
        title="dd/mm/yyyy"
        autoComplete="off"
        aria-invalid={isoValue === null || undefined}
        onChange={(event) => change(event.target.value)}
      />
      <button
        className={styles.pickerButton}
        type="button"
        aria-label={`Mở lịch: ${label}`}
        title={`Chọn ${label.toLocaleLowerCase("vi")}`}
        disabled={props.disabled || props.readOnly}
        onClick={openPicker}
      >
        <CalendarDays size={17} aria-hidden="true" />
      </button>
      <input
        ref={picker}
        className={styles.nativePicker}
        type="date"
        value={isoValue ?? ""}
        min={props.min}
        max={props.max}
        disabled={props.disabled || props.readOnly}
        aria-hidden="true"
        tabIndex={-1}
        onChange={(event) => change(event.target.value)}
      />
    </div>
  );
}
