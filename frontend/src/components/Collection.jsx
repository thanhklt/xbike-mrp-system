import { useId, useState } from "react";
import { ArrowDownUp, CalendarDays, ChevronDown, ChevronUp, Filter, LayoutGrid, Layers, Search } from "lucide-react";
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
  searchPlaceholder = "Tìm mã hoặc tên…",
  title = "Danh sách",
  validate,
  expandableFilters = false,
  filterIcon = false,
}) {
  const [draft, setDraft] = useState(collection.params);
  const [filterError, setFilterError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const advancedId = useId();
  const icons = { trang_thai: Layers, loai_yeu_cau: LayoutGrid, sort: ArrowDownUp, tu_ngay: CalendarDays, den_ngay: CalendarDays };
  function renderFilter(field) {
    const Icon = expandableFilters && icons[field.name];
    return (
      <Field
        key={field.name}
        {...field}
        label={Icon ? <><Icon size={19} aria-hidden="true" />{field.label}</> : field.label}
        value={draft[field.name] ?? ""}
        onChange={(event) => setDraft({ ...draft, [field.name]: event.target.value })}
      />
    );
  }
  const searchInput = search && (
      <Field
        label={expandableFilters ? <><Search size={19} aria-hidden="true" />Tìm kiếm</> : "Tìm kiếm"}
        name="q"
        type="search"
        placeholder={searchPlaceholder}
        value={draft.q || ""}
        onChange={(event) => setDraft({ ...draft, q: event.target.value })}
      />
  );
  const searchField = expandableFilters && search ? (
    <div className="employee-filter-search">
      {searchInput}
      <Search className="employee-filter-search-icon" size={20} aria-hidden="true" />
    </div>
  ) : searchInput;
  return (
    <Card title={title} className={expandableFilters ? "employee-request-collection" : ""}>
      <form
        className={expandableFilters ? "filters employee-request-filters" : "filters"}
        onSubmit={(event) => {
          event.preventDefault();
          const message = validate?.(draft) ?? null;
          setFilterError(message);
          if (!message) collection.filter(draft);
        }}
      >
        {expandableFilters ? (
          <>
            <div className="employee-filter-primary">
              {searchField}
              {filters.filter((field) => field.name === "trang_thai").map(renderFilter)}
              <Button type="submit"><Filter size={20} aria-hidden="true" />Lọc</Button>
            </div>
            <div id={advancedId} className="employee-filter-advanced" hidden={!expanded}>
              {filters.filter((field) => field.name !== "trang_thai").map(renderFilter)}
            </div>
            <div className="employee-filter-toggle">
              <button type="button" aria-expanded={expanded} aria-controls={advancedId} onClick={() => setExpanded(!expanded)}>
                {expanded ? "Ẩn bớt" : "Hiện thêm"}
                {expanded ? <ChevronUp size={19} aria-hidden="true" /> : <ChevronDown size={19} aria-hidden="true" />}
              </button>
            </div>
          </>
        ) : <>{searchField}{filters.map(renderFilter)}<Button type="submit" variant="secondary">{filterIcon && <Filter size={20} aria-hidden="true" />}Lọc</Button></>}
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
