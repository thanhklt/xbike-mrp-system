import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { ITEM_LABELS, money, number, dateTime, unitLabel } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ErrorNotice, QueryState } from "../../components/QueryState.jsx";
import { DocumentLines, newLine, itemTypeOptions } from "../../components/ResourceFields.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
import { itemPayload, itemUnitOptions } from "./itemForm.js";
const warehouseTypes = [
  { value: "", label: "Tất cả" },
  { value: "linh_kien", label: "Linh kiện" },
  { value: "thanh_pham", label: "Thành phẩm" },
];
export function MaterialsPage({ readOnly = false }) {
  const base = readOnly ? "/nv/ton-kho" : "/kho/mat-hang";
  const { id } = useParams();
  const collection = useCollection(API.items, { sort: readOnly ? "id" : "ma_mat_hang" });
  const detail = useDetail(API.items, id);
  return (
    <>
      <PageHeader
        title={readOnly ? "Tra cứu tồn kho" : "Mặt hàng và tồn kho"}
        subtitle={
          readOnly
            ? "NVL · Linh kiện · Bán thành phẩm · Thành phẩm. Tồn kho chỉ thay đổi qua chứng từ đã ghi sổ."
            : "Quản lý linh kiện, thành phẩm và số lượng tồn, đang giữ, còn dùng. Tồn chỉ đổi qua chứng từ đã ghi sổ."
        }
        action={
          !readOnly && (
            <Link className="btn btn-primary" to={`${base}/moi`}>
              Thêm mặt hàng
            </Link>
          )
        }
      />
      <div>
        <Collection
          collection={collection}
          allowReset={!readOnly}
          pageSizes={readOnly ? undefined : [20, 50, 100]}
          validate={({ loai_mat_hang, is_active }) =>
            loai_mat_hang === "linh_kien" && ["true", "false"].includes(String(is_active))
              ? "Linh kiện không có trạng thái"
              : null
          }
          filters={[
            {
              name: "loai_mat_hang",
              label: "Loại mặt hàng",
              as: "select",
              options: readOnly ? itemTypeOptions : warehouseTypes,
            },
            {
              name: "is_active",
              label: "Trạng thái",
              as: "select",
              options: [
                { value: "", label: "Tất cả" },
                { value: "true", label: "Đang sử dụng" },
                { value: "false", label: "Ngừng sử dụng" },
              ],
            },
            {
              name: "sort",
              label: "Sắp xếp",
              as: "select",
              options: readOnly
                ? [
                    { value: "id", label: "ID tăng dần" },
                    { value: "ten_mat_hang", label: "Tên mặt hàng" },
                    { value: "-don_gia", label: "Đơn giá giảm dần" },
                  ]
                : [
                    { value: "ma_mat_hang", label: "Mã tăng dần" },
                    { value: "-ma_mat_hang", label: "Mã giảm dần" },
                    { value: "don_gia", label: "Đơn giá tăng dần" },
                    { value: "-don_gia", label: "Đơn giá giảm dần" },
                  ],
            },
          ]}
          columns={[
            {
              key: "ma_mat_hang",
              label: "Mã",
              render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_mat_hang}</Link>,
            },
            {
              key: "ten_mat_hang",
              label: "Tên mặt hàng",
              render: (row) => (
                <>
                  <strong>{row.ten_mat_hang}</strong>
                  <small>{ITEM_LABELS[row.loai_mat_hang]}</small>
                </>
              ),
            },
            { key: "sku", label: "SKU" },
            {
              key: "so_luong_ton",
              label: readOnly ? "Tồn kho" : "Tồn thực tế",
              numeric: true,
              render: (row) => (
                <>
                  {number(row.so_luong_ton)}
                  <small>{unitLabel(row.don_vi_tinh)}</small>
                </>
              ),
            },
            ...(!readOnly
              ? [
                  {
                    key: "so_luong_dang_giu",
                    label: "Đang giữ",
                    numeric: true,
                    render: (row) => number(row.so_luong_dang_giu),
                  },
                  {
                    key: "so_luong_con_dung",
                    label: "Còn dùng",
                    numeric: true,
                    render: (row) => number(row.so_luong_con_dung),
                  },
                ]
              : []),
            ...(!readOnly
              ? [
                  {
                    key: "don_gia",
                    label: "Đơn giá",
                    numeric: true,
                    render: (row) => money(row.don_gia),
                  },
                ]
              : []),
            {
              key: "is_active",
              label: "Trạng thái",
              render: (row) =>
                row.loai_mat_hang === "linh_kien" ? (
                  "—"
                ) : (
                  <Badge status={row.is_active ? "hoat_dong" : "bi_khoa"}>
                    {row.is_active ? "Đang dùng" : "Ngừng dùng"}
                  </Badge>
                ),
            },
            {
              key: "action",
              label: "Thao tác",
              render: (row) => (
                <Link
                  className={readOnly ? undefined : "warehouse-item-edit"}
                  to={`${base}/${row.id}`}
                >
                  {readOnly ? "Xem" : "Sửa"} →
                </Link>
              ),
            },
          ]}
        />
        <RecordPanel
          id={id}
          query={detail}
          base={base}
          title={id === "moi" ? "Thêm mặt hàng" : "Chi tiết mặt hàng"}
        >
          {(snapshot) =>
            readOnly ? (
              <InfoGrid
                entries={[
                  ["Tên mặt hàng", snapshot?.data.ten_mat_hang],
                  ["SKU", snapshot?.data.sku],
                  ["Tồn kho", number(snapshot?.data.so_luong_ton)],
                  ["Đơn vị tính", unitLabel(snapshot?.data.don_vi_tinh)],
                  ["Cập nhật tồn", dateTime(snapshot?.data.ton_kho_updated_at)],
                ]}
              />
            ) : (
              <ItemForm snapshot={snapshot} />
            )
          }
        </RecordPanel>
      </div>
    </>
  );
}
function ItemForm({ snapshot }) {
  const record = snapshot?.data;
  const navigate = useNavigate();
  const { confirm, notify } = useFeedback();
  const action = useWrite();
  const { save, busy, error } = useSave();
  const catalog = useCatalog();
  const [search] = useSearchParams();
  const [lines, setLines] = useState([newLine()]);
  const [values, setValues] = useState({
    ten_mat_hang: record?.ten_mat_hang || "",
    sku: record?.sku || "",
    loai_mat_hang:
      record?.loai_mat_hang ||
      (search.get("loai_mat_hang") === "thanh_pham" ? "thanh_pham" : "linh_kien"),
    don_vi_tinh: record?.don_vi_tinh || "cai",
    mau_sac: record?.mau_sac || "",
    mo_ta: record?.mo_ta || "",
    don_gia: record?.don_gia ?? "",
  });
  const field = (name) => ({
    value: values[name],
    onChange: (event) => setValues({ ...values, [name]: event.target.value }),
  });
  function submit(event) {
    event.preventDefault();
    const body = itemPayload(values, { record, lines });
    save(
      {
        path: record ? `${API.items}/${record.id}` : API.items,
        method: record ? "patch" : "post",
        body,
        etag: snapshot?.etag,
        versioned: Boolean(record),
      },
      (result) => navigate(`/kho/mat-hang/${result.data.id}`),
    );
  }
  return (
    <form className="stack" onSubmit={submit}>
      <ErrorNotice error={error} />
      <div className="form-grid">
        <Field label="SKU" required {...field("sku")} />
        <Field label="Tên mặt hàng" required {...field("ten_mat_hang")} />
        <Field
          as="select"
          label="Loại mặt hàng"
          required
          options={warehouseTypes.slice(1)}
          disabled={Boolean(record)}
          {...field("loai_mat_hang")}
        />
        <Field
          as="select"
          label="Đơn vị tính"
          required
          options={itemUnitOptions(record?.don_vi_tinh)}
          {...field("don_vi_tinh")}
        />
        <Field
          label="Màu sắc"
          pattern="[a-z]+(_[a-z]+)*"
          placeholder="den, trang…"
          {...field("mau_sac")}
        />
        <Field
          label="Đơn giá (VND)"
          required
          type="number"
          min="0"
          max={Number.MAX_SAFE_INTEGER}
          step="1"
          {...field("don_gia")}
        />
      </div>
      {!record && values.loai_mat_hang === "thanh_pham" && (
        <QueryState query={catalog}>
          <h3>Định mức đầu tiên cho một thành phẩm</h3>
          <DocumentLines
            lines={lines}
            onChange={setLines}
            items={catalog.data?.data || []}
            types={["linh_kien"]}
          />
        </QueryState>
      )}
      <Field as="textarea" label="Mô tả" rows={3} {...field("mo_ta")} />
      {record && (
        <>
          <div className="warehouse-stock-summary">
            {[
              ["Tồn thực tế", record.so_luong_ton],
              ["Đang giữ", record.so_luong_dang_giu],
              ["Còn dùng", record.so_luong_con_dung],
            ].map(([label, value]) => (
              <div key={label}>
                <span className="muted">{label}</span>
                <strong>
                  {number(value)} <small>{unitLabel(record.don_vi_tinh)}</small>
                </strong>
              </div>
            ))}
          </div>
        </>
      )}
      <div className="actions actions-end">
        {record?.loai_mat_hang === "thanh_pham" && (
          <Button
            variant={record.is_active ? "danger" : "secondary"}
            onClick={() =>
              confirm({
                title: record.is_active ? "Ngừng sử dụng mặt hàng" : "Dùng lại thành phẩm",
                description: `${record.ma_mat_hang} · ${record.ten_mat_hang}. Mặt hàng ngừng hoạt động không được dùng trong chứng từ mới.`,
                impact: record.is_active
                  ? "Mặt hàng, số dư tồn và chứng từ cũ vẫn sẽ được giữ nguyên số lượng nhưng không thể sử dụng mặt hàng."
                  : "Backend kiểm tra và dùng lại công thức ngừng gần nhất; không thay đổi tồn kho.",
                danger: record.is_active,
                onConfirm: async () => {
                  await action.mutateAsync({
                    path: `${API.items}/${record.id}`,
                    method: record.is_active ? "delete" : "patch",
                    body: record.is_active ? null : { is_active: true },
                    etag: snapshot.etag,
                  });
                  notify(
                    record.is_active ? "Đã ngừng sử dụng mặt hàng." : "Đã dùng lại thành phẩm.",
                  );
                },
              })
            }
          >
            {record.is_active ? "Ngừng sử dụng…" : "Dùng lại thành phẩm"}
          </Button>
        )}
        <Button
          type="submit"
          disabled={
            busy || (!record && values.loai_mat_hang === "thanh_pham" && !catalog.isSuccess)
          }
        >
          {busy ? "Đang lưu…" : "Lưu"}
        </Button>
      </div>
    </form>
  );
}
