// Range filters display day/month/year while API queries keep ISO calendar dates.
export function dateFilterIsoValue(value) {
  if (!value) return "";
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  const display = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  if (!iso && !display) return null;
  const [, year, month, day] = iso ?? [display[0], display[3], display[2], display[1]];
  if (Number(year) < 1) return null;
  const date = new Date(0);
  date.setUTCFullYear(Number(year), Number(month) - 1, Number(day));
  if (
    date.getUTCFullYear() !== Number(year) ||
    date.getUTCMonth() + 1 !== Number(month) ||
    date.getUTCDate() !== Number(day)
  )
    return null;
  return `${year}-${month}-${day}`;
}

export function dateFilterDisplayValue(value) {
  const iso = dateFilterIsoValue(value);
  if (!iso) return value ?? "";
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}
