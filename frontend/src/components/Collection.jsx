import { useEffect, useId, useRef, useState } from "react";
import { ArrowDownUp, CalendarDays, ChevronDown, ChevronUp, Filter, LayoutGrid, Layers, RotateCcw, Search } from "lucide-react";
import { Card } from "./Card.jsx";
import { Button } from "./Button.jsx";
import { Field } from "./Field.jsx";
import { DateInput } from "./DateInput.jsx";
import { dateRangeError } from "./filterFields.js";
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
  searchPlaceholder = "Tìm mã hoặc tên…",
  title = "Danh sách",
  validate,
  expandableFilters = false,
  filterIcon = false,
  cycleFilters = false,
  syncDraftWithParams = false,
  allowReset = false,
  pageSizes,
  optionLabels = {},
}) {
  const [draft, setDraft] = useState(() => filterParams(collection.params));
  const [initial] = useState(() => filterParams(collection.params));
  const [filterError, setFilterError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [resetCount, setResetCount] = useState(0);
  const searchTimer = useRef(null);
  const pendingSearch = useRef(null);
  const advancedId = useId();

  useEffect(() => {
    if (syncDraftWithParams || cycleFilters) {
      const next = filterParams(collection.params);
      const pending = pendingSearch.current;
      if (cycleFilters && pending !== null && pending !== (next.q ?? "")) {
        const nextWithSearch = { ...next, q: pending };
        setDraft(nextWithSearch);
        apply(nextWithSearch);
        return;
      }
      clearTimeout(searchTimer.current);
      pendingSearch.current = null;
      setDraft(next);
      setFilterError(null);
    }
  }, [collection.params, syncDraftWithParams, cycleFilters]);
  useEffect(() => () => clearTimeout(searchTimer.current), []);
  const icons = { trang_thai: Layers, loai_yeu_cau: LayoutGrid, sort: ArrowDownUp, tu_ngay: CalendarDays, den_ngay: CalendarDays };
  function apply(next) {
    clearTimeout(searchTimer.current);
    const message = (cycleFilters ? dateRangeError(next) : null) ?? validate?.(next) ?? null;
    setFilterError(message);
    if (!message) collection.filter(next);
    pendingSearch.current = null;
  }
  function resetFilters() {
    clearTimeout(searchTimer.current);
    pendingSearch.current = null;
    const next = search ? { q: "" } : {};
    for (const field of filters) next[field.name] = field.options?.[0]?.value ?? "";
    setDraft({ ...filterParams(collection.params), ...next });
    setFilterError(null);
    setResetCount((count) => count + 1);
    collection.reset(next);
  }
  function renderFilter(field) {
    const Icon = expandableFilters && icons[field.name];
    const labelContent = Icon ? <><Icon size={19} aria-hidden="true" />{field.label}</> : field.label;
    const options = field.options?.map((option) => ({
      ...option,
      label: optionLabels[field.name]?.[option.value] ?? option.label,
    }));
    if (cycleFilters && field.as === "select") {
      const fieldId = `filter-${field.name}`;
      const SelectIcon = icons[field.name] || Filter;
      return (
        <div key={field.name} className="field">
          <div className="field-label">
            <label htmlFor={fieldId}>{field.label}</label>
          </div>
          <div className="admin-select-shell">
            <SelectIcon size={18} aria-hidden="true" />
            <select
              id={fieldId}
              name={field.name}
              value={draft[field.name] ?? ""}
              disabled={field.disabled}
              onChange={(event) => {
                const next = { ...draft, [field.name]: event.target.value };
                setDraft(next);
                apply(next);
              }}
            >
              {options?.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
        </div>
      );
    }
    return (
      <Field
        key={field.type === "date" ? `${field.name}-${resetCount}` : field.name}
        {...field}
        options={options}
        {...(field.type === "date" ? { as: DateInput, type: undefined } : {})}
        label={labelContent}
        value={draft[field.name] ?? ""}
        onChange={(event) => {
          const next = { ...draft, [field.name]: event.target.value };
          setDraft(next);
          if (field.as === "select") apply(next);
          else if (cycleFilters && field.type === "date") apply(next);
        }}
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
        onChange={(event) => {
          const next = { ...draft, q: event.target.value };
          setDraft(next);
          if (cycleFilters) {
            clearTimeout(searchTimer.current);
            pendingSearch.current = next.q;
            searchTimer.current = setTimeout(() => apply(next), 300);
          }
        }}
      />
  );
  const searchField = expandableFilters && search ? (
    <div className="employee-filter-search">
      {searchInput}
      <Search className="employee-filter-search-icon" size={20} aria-hidden="true" />
    </div>
  ) : searchInput;
  const filterAction = cycleFilters ? (
    <Button type="button" variant={expandableFilters ? "primary" : "secondary"} onClick={resetFilters}>
      <RotateCcw size={20} aria-hidden="true" />Reset tìm kiếm
    </Button>
  ) : (
    <div className="filter-actions">
      <Button type="submit" variant={expandableFilters ? "primary" : "secondary"}>
        {(expandableFilters || filterIcon) && <Filter size={20} aria-hidden="true" />}Lọc
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
  );
  return (
    <Card title={title} className={expandableFilters ? "employee-request-collection" : ""}>
      <form
        className={expandableFilters ? "filters employee-request-filters" : "filters"}
        onSubmit={(event) => {
          event.preventDefault();
          apply(draft);
        }}
      >
        {expandableFilters ? (
          <>
            <div className="employee-filter-primary">
              {searchField}
              {filters.filter((field) => field.name === "trang_thai").map(renderFilter)}
              {filterAction}
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
        ) : <>{searchField}{filters.map(renderFilter)}{filterAction}</>}
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
          onPage={(page) => {
            if (cycleFilters && (draft.q || "") !== (collection.params.q || "")) apply(draft);
            else collection.setPage(page);
          }}
          pageSizes={pageSizes}
          onPageSize={collection.setPageSize}
        />
      </QueryState>
    </Card>
  );
}
