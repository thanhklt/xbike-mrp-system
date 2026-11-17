import { useState } from "react";
import { Card } from "./Card.jsx";
import { Button } from "./Button.jsx";
import { Field } from "./Field.jsx";
import { DateInput } from "./DateInput.jsx";
import { DataTable, Pagination } from "./DataTable.jsx";
import { QueryState } from "./QueryState.jsx";
export function Collection({
  collection,
  columns,
  filters = [],
  search = true,
  title = "Danh sách",
  validate,
}) {
  const [draft, setDraft] = useState(collection.params);
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
            {...(field.type === "date" ? { as: DateInput, type: undefined } : {})}
            value={draft[field.name] ?? ""}
            onChange={(event) => {
              const next = { ...draft, [field.name]: event.target.value };
              setDraft(next);
              if (field.as === "select") apply(next);
            }}
          />
        ))}
        <Button type="submit" variant="secondary">
          Lọc
        </Button>
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
        />
      </QueryState>
    </Card>
  );
}
