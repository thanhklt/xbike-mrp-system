import { useState } from "react";
import { Card } from "./Card.jsx";
import { Button } from "./Button.jsx";
import { Field } from "./Field.jsx";
import { DataTable, Pagination } from "./DataTable.jsx";
import { QueryState } from "./QueryState.jsx";
export function Collection({
  collection,
  columns,
  filters = [],
  search = true,
  title = "Danh sách",
}) {
  const [draft, setDraft] = useState(collection.params);
  return (
    <Card title={title}>
      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          collection.filter(draft);
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
            value={draft[field.name] ?? ""}
            onChange={(event) => setDraft({ ...draft, [field.name]: event.target.value })}
          />
        ))}
        <Button type="submit" variant="secondary">
          Lọc
        </Button>
      </form>
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
