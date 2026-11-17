export function maskDmy(text) {
  const digits = String(text ?? "").replace(/\D/g, "").slice(0, 8);
  return [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4)].filter(Boolean).join("/");
}

export function dmyToIso(text) {
  if (!/^\d{2}\/\d{2}\/\d{4}$/.test(text)) return null;
  const [day, month, year] = text.split("/").map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1]) return null;
  return `${text.slice(6)}-${text.slice(3, 5)}-${text.slice(0, 2)}`;
}

export function isoToDmy(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
  const display = `${value.slice(8)}/${value.slice(5, 7)}/${value.slice(0, 4)}`;
  return dmyToIso(display) === value ? display : "";
}
