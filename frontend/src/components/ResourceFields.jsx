import { Field } from "./Field.jsx";
import { Button } from "./Button.jsx";
import { DataTable } from "./DataTable.jsx";
import { itemName, ITEM_LABELS, STATUS_LABELS, money, number } from "../lib/format.js";
export const statusFilter = (statuses) => ({
  name: "trang_thai",
  label: "Trạng thái",
  as: "select",
  options: [
    { value: "", label: "Tất cả" },
    ...statuses.map((value) => ({ value, label: STATUS_LABELS[value] })),
  ],
});
export const dateFilters = [
  { name: "tu_ngay", label: "Từ ngày", type: "date" },
  { name: "den_ngay", label: "Đến ngày", type: "date" },
];
export function ItemSelect({ items = [], label = "Mặt hàng", value, onChange, types, ...props }) {
  const choices = items.filter(
    (item) =>
      (item.is_active && (!types || types.includes(item.loai_mat_hang))) ||
      item.id === Number(value),
  );
  return (
    <Field as="select" label={label} value={value ?? ""} onChange={onChange} {...props}>
      <option value="">Chọn mặt hàng</option>
      {choices.map((item) => (
        <option key={item.id} value={item.id}>
          {item.ma_mat_hang} · {item.ten_mat_hang}
          {!item.is_active ? " (ngừng hoạt động)" : ""}
        </option>
      ))}
    </Field>
  );
}
export function EmployeeSelect({
  employees = [],
  value,
  onChange,
  required = false,
  label = "Nhân viên phụ trách",
}) {
  const candidates = employees.filter(
    (employee) =>
      (employee.ma_vai_tro === "nhan_vien" && employee.trang_thai === "hoat_dong") ||
      employee.id === Number(value),
  );
  return (
    <Field as="select" label={label} value={value ?? ""} onChange={onChange} required={required}>
      <option value="">Chưa giao</option>
      {candidates.map((employee) => (
        <option key={employee.id} value={employee.id}>
          {employee.ma_nhan_vien} · {employee.ho_ten || "Chưa có họ tên"}
          {employee.trang_thai !== "hoat_dong" ? " (bị khóa)" : ""}
        </option>
      ))}
    </Field>
  );
}
export function newLine(values = {}) {
  return { key: crypto.randomUUID(), mat_hang_id: "", so_luong: "1", don_gia_thuc: "0", ...values };
}
export function DocumentLines({ lines, onChange, items = [], prices = false, types, outputId }) {
  function update(key, patch) {
    onChange(lines.map((line) => (line.key === key ? { ...line, ...patch } : line)));
  }
  const available = items.filter(
    (item) =>
      item.is_active &&
      item.id !== Number(outputId) &&
      (!types || types.includes(item.loai_mat_hang)),
  );
  return (
    <div>
      <div className="table-scroll">
        <table className="line-editor">
          <thead>
            <tr>
              <th className="item-column">Mặt hàng</th>
              <th className="quantity-column numeric">Số lượng</th>
              {prices && <th className="quantity-column numeric">Đơn giá (đ)</th>}
              <th>ĐVT</th>
              <th>Xóa</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={line.key}>
                <td>
                  <select
                    aria-label={`Mặt hàng dòng ${index + 1}`}
                    required
                    value={line.mat_hang_id}
                    onChange={(event) => update(line.key, { mat_hang_id: event.target.value })}
                  >
                    <option value="">Chọn mặt hàng</option>
                    {[
                      ...available,
                      ...items.filter(
                        (item) =>
                          item.id === Number(line.mat_hang_id) &&
                          !available.some((candidate) => candidate.id === item.id),
                      ),
                    ].map((item) => (
                      <option
                        key={item.id}
                        value={item.id}
                        disabled={
                          item.id !== Number(line.mat_hang_id) &&
                          lines.some(
                            (other) =>
                              other.key !== line.key && Number(other.mat_hang_id) === item.id,
                          )
                        }
                      >
                        {item.ma_mat_hang} · {item.ten_mat_hang}
                        {!item.is_active ? " (ngừng hoạt động)" : ""}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    aria-label={`Số lượng dòng ${index + 1}`}
                    required
                    type="number"
                    min="1"
                    max="2147483647"
                    step="1"
                    value={line.so_luong}
                    onChange={(event) => update(line.key, { so_luong: event.target.value })}
                  />
                </td>
                {prices && (
                  <td>
                    <input
                      aria-label={`Đơn giá dòng ${index + 1}`}
                      required
                      type="number"
                      min="0"
                      max={Number.MAX_SAFE_INTEGER}
                      step="1"
                      value={line.don_gia_thuc}
                      onChange={(event) => update(line.key, { don_gia_thuc: event.target.value })}
                    />
                  </td>
                )}
                <td>
                  {items.find((item) => item.id === Number(line.mat_hang_id))?.don_vi_tinh || "—"}
                </td>
                <td>
                  <Button
                    variant="secondary"
                    disabled={lines.length === 1}
                    aria-label={`Xóa dòng ${index + 1}`}
                    onClick={() =>
                      onChange(lines.filter((candidate) => candidate.key !== line.key))
                    }
                  >
                    ×
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="line-add">
        <Button variant="secondary" onClick={() => onChange([...lines, newLine()])}>
          + Thêm dòng
        </Button>
      </div>
    </div>
  );
}
export function linePayload(lines, prices = false) {
  return lines.map((line) => ({
    mat_hang_id: Number(line.mat_hang_id),
    so_luong: Number(line.so_luong),
    ...(prices ? { don_gia_thuc: Number(line.don_gia_thuc) } : {}),
  }));
}
export function SavedLines({ lines = [], items = [], prices = false }) {
  return (
    <DataTable
      rows={lines.map((line, index) => ({ ...line, id: line.id ?? index }))}
      columns={[
        {
          key: "mat_hang_id",
          label: "Mặt hàng",
          render: (line) => (
            <>
              <strong>{itemName(items, line.mat_hang_id)}</strong>
              <small>
                {items.find((item) => item.id === line.mat_hang_id)?.ma_mat_hang ||
                  `#${line.mat_hang_id}`}
              </small>
            </>
          ),
        },
        {
          key: "so_luong",
          label: "Số lượng",
          numeric: true,
          render: (line) => number(line.so_luong),
        },
        ...(prices
          ? [
              {
                key: "don_gia_thuc",
                label: "Đơn giá",
                numeric: true,
                render: (line) => money(line.don_gia_thuc),
              },
              {
                key: "tong_gia",
                label: "Thành tiền",
                numeric: true,
                render: (line) => money(line.tong_gia),
              },
            ]
          : []),
      ]}
    />
  );
}
export const itemTypeOptions = [
  { value: "", label: "Tất cả loại" },
  ...Object.entries(ITEM_LABELS).map(([value, label]) => ({ value, label })),
];
