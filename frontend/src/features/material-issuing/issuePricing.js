export function pricedIssue(record, items) {
  const prices = new Map(items.map((item) => [item.id, item.don_gia]));
  const lines = record.chi_tiet.map((line) => {
    const unitPrice = line.don_gia_thuc ?? prices.get(line.mat_hang_id) ?? null;
    const lineTotal = line.tong_gia ?? (unitPrice === null ? null : line.so_luong * unitPrice);
    return { ...line, don_gia_thuc: unitPrice, tong_gia: lineTotal };
  });

  const total = record.tong_tien ?? (lines.some((line) => line.tong_gia === null)
    ? null
    : lines.reduce((sum, line) => sum + Number(line.tong_gia), 0));
  return { lines, total };
}
