import { Button } from "./Button.jsx";
import { number } from "../lib/format.js";
export function DataTable({ columns, rows = [], empty = "Chưa có dữ liệu phù hợp.", caption }) {
  return (
    <div className="table-scroll">
      <table>
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={column.numeric ? "numeric" : ""}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => (
              <tr key={row.id}>
                {columns.map((column) => (
                  <td key={column.key} className={column.numeric ? "numeric" : ""}>
                    {column.render ? column.render(row) : (row[column.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length} className="empty-state">
                {empty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
export function Pagination({ meta = {}, onPage, busy }) {
  const { page = 1, page_size: pageSize = 20, total = 0, total_pages: totalPages = 0 } = meta;
  return (
    <div className="pagination">
      <span className="muted">
        {total
          ? `${number((page - 1) * pageSize + 1)}–${number(Math.min(page * pageSize, total))} trong ${number(total)} kết quả`
          : "0 kết quả"}
      </span>
      <div className="actions">
        <Button
          variant="secondary"
          disabled={busy || page <= 1}
          onClick={() => onPage(page - 1)}
          aria-label="Trang trước"
        >
          ‹
        </Button>
        <span>
          Trang {page} / {Math.max(totalPages, 1)}
        </span>
        <Button
          variant="secondary"
          disabled={busy || page >= totalPages}
          onClick={() => onPage(page + 1)}
          aria-label="Trang sau"
        >
          ›
        </Button>
      </div>
    </div>
  );
}
