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

export function buildPageSequence(current, total) {
  const totalPages = Math.max(Number(total) || 1, 1);
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }
  if (current <= 3) {
    return [1, 2, 3, "...", totalPages];
  }
  if (current >= totalPages - 2) {
    return [1, "...", totalPages - 2, totalPages - 1, totalPages];
  }
  return [1, "...", current - 1, current, current + 1, "...", totalPages];
}

export function AdminPagination({
  page = 1,
  pageSize = 10,
  totalPages = 1,
  busy = false,
  onPage,
  onPageSize,
}) {
  const safeTotalPages = Math.max(Number(totalPages) || 1, 1);
  const pages = buildPageSequence(page, safeTotalPages);
  return (
    <div className="admin-pagination">
      <div className="admin-page-size">
        <span>Hiển thị</span>
        <select
          aria-label="Số dòng mỗi trang"
          value={pageSize}
          disabled={busy}
          onChange={(event) => onPageSize?.(Number(event.target.value))}
        >
          <option value={10}>10</option>
        </select>
        <span>dòng / trang</span>
      </div>
      <div className="admin-page-numbers" role="navigation" aria-label="Phân trang">
        <button
          type="button"
          className="admin-page-btn"
          aria-label="Trang trước"
          disabled={busy || page <= 1}
          onClick={() => onPage(page - 1)}
        >
          ‹
        </button>
        {pages.map((entry, index) =>
          entry === "..." ? (
            <span key={`ellipsis-${index}`} className="admin-page-ellipsis" aria-hidden="true">
              …
            </span>
          ) : (
            <button
              key={entry}
              type="button"
              className={`admin-page-btn ${entry === page ? "is-active" : ""}`}
              aria-label={`Trang ${entry}`}
              aria-current={entry === page ? "page" : undefined}
              disabled={busy}
              onClick={() => onPage(entry)}
            >
              {entry}
            </button>
          ),
        )}
        <button
          type="button"
          className="admin-page-btn"
          aria-label="Trang sau"
          disabled={busy || page >= safeTotalPages}
          onClick={() => onPage(page + 1)}
        >
          ›
        </button>
      </div>
    </div>
  );
}
