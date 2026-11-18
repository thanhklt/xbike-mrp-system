import { useState } from "react";
import { Card } from "./Card.jsx";
import { Button } from "./Button.jsx";
import { Field } from "./Field.jsx";
import { DateInput } from "./DateInput.jsx";
import { DataTable, Pagination } from "./DataTable.jsx";
import { QueryState } from "./QueryState.jsx";

// Bộ lọc không mang theo phân trang: giữ số dòng/trang người dùng đã chọn.
function filterParams({ page: _page, page_size: _pageSize, ...filters }) {
  return filters;
}
export function Collection({
  collection,
  columns,
  filters = [],
  search = true,
  title = "Danh sách",
  validate,
  allowReset = false,
  pageSizes,
  optionLabels = {},
}) {
  const [draft, setDraft] = useState(() => filterParams(collection.params));
  const [initial] = useState(() => filterParams(collection.params));
  const [filterError, setFilterError] = useState(null);
  function apply(next) {
    const message = validate?.(next) ?? null;
    setFilterError(message);
    if (!message) collection.filter(next);
  }
  return (
    <Card title={title}>
      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          apply(draft);
        }}
      >
        {search && (
          <Field
            label="Tìm kiếm"
            name="q"
            type="search"
            placeholder="Tìm mã hoặc tên…"
            value={draft.q || ""}
            onChange={(event) => setDraft({ ...draft, q: event.target.value })}
          />
        )}
        {filters.map((field) => (
          <Field
            key={field.name}
            {...field}
            options={field.options?.map((option) => ({
              ...option,
              label: optionLabels[field.name]?.[option.value] ?? option.label,
            }))}
            {...(field.type === "date" ? { as: DateInput, type: undefined } : {})}
            value={draft[field.name] ?? ""}
            onChange={(event) => {
              const next = { ...draft, [field.name]: event.target.value };
              setDraft(next);
              if (field.as === "select") apply(next);
            }}
          />
        ))}
        <div className="filter-actions">
          <Button type="submit" variant="secondary">
            Lọc
          </Button>
          {allowReset && (
            <Button
              variant="secondary"
              onClick={() => {
                const cleared = Object.fromEntries(
                  Object.keys(draft).map((key) => [key, initial[key] ?? ""]),
                );
                setDraft(cleared);
                setFilterError(null);
                collection.filter(cleared);
              }}
            >
              Xóa lọc
            </Button>
          )}
        </div>
      </form>
      {filterError && (
        <div className="notice notice-error" role="alert">
          {filterError}
        </div>
      )}
      <QueryState query={collection.query}>
        <DataTable columns={columns} rows={collection.query.data?.data} caption={title} />
        <Pagination
          meta={collection.query.data?.meta}
          busy={collection.query.isFetching}
          onPage={collection.setPage}
          pageSizes={pageSizes}
          onPageSize={collection.setPageSize}
        />
      </QueryState>
    </Card>
  );
}
