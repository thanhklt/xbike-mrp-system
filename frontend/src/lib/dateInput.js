export function maskDmy(text, shortYear = false) {
  const maxDigits = shortYear ? 6 : 8;
  const digits = String(text ?? "").replace(/\D/g, "").slice(0, maxDigits);
  return [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4)].filter(Boolean).join("/");
}

export function dmyToIso(text, shortYear = false) {
  if (shortYear) {
    if (!/^\d{2}\/\d{2}\/\d{2}$/.test(text)) return null;
    const [day, month, yy] = text.split("/");
    const fullText = `${day}/${month}/20${yy}`;
    return dmyToIso(fullText, false);
  }
  if (!/^\d{2}\/\d{2}\/\d{4}$/.test(text)) return null;
  const [day, month, year] = text.split("/").map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1]) return null;
  return `${text.slice(6)}-${text.slice(3, 5)}-${text.slice(0, 2)}`;
}

export function isoToDmy(value, shortYear = false) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
  const dmy4 = `${value.slice(8)}/${value.slice(5, 7)}/${value.slice(0, 4)}`;
  if (dmyToIso(dmy4, false) !== value) return "";
  return shortYear ? `${value.slice(8)}/${value.slice(5, 7)}/${value.slice(2, 4)}` : dmy4;
}
