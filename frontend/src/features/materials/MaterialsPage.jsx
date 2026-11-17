import { useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import {
  ITEM_LABELS,
  ITEM_TYPES,
  money,
  nullable,
  number,
  dateTime,
  unitLabel,
  colorLabel,
  quantity,
} from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { AdminStatusBadge, Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ErrorNotice, Notice } from "../../components/QueryState.jsx";
import { itemTypeOptions } from "../../components/ResourceFields.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
const modes = {
  manage: { base: "/kho/mat-hang", title: "Mặt hàng và tồn kho", showPrice: true },
  employee: { base: "/nv/ton-kho", title: "Tra cứu tồn kho", showPrice: false },
  admin: { base: "/admin/mat-hang", title: "Tra cứu mặt hàng", showPrice: true },
};

export function MaterialsPage({ mode = "manage" }) {
  const { base, title, showPrice } = modes[mode];
  const readOnly = mode !== "manage";
  const { id } = useParams();
  const collection = useCollection(API.items, { sort: "id" });
  const detail = useDetail(API.items, id);
  if (readOnly && id === "moi") return <Navigate to={base} replace />;
  return (
    <>
      {mode === "admin" ? (
        <PageHeader variant="large" title={title} />
      ) : (
        <PageHeader
          title={title}
          subtitle="Linh kiện · Thành phẩm. Tồn kho chỉ thay đổi qua chứng từ đã ghi sổ."
          action={
            !readOnly && (
              <Link className="btn btn-primary" to={`${base}/moi`}>
                Thêm mặt hàng
              </Link>
            )
          }
        />
      )}
      <div>
        <Collection
          collection={collection}
          validate={(draft) =>
            draft.loai_mat_hang === "linh_kien" && (draft.is_active ?? "") !== ""
              ? "Trạng thái chỉ lọc được cho thành phẩm."
              : null
          }
          filters={[
            {
              name: "loai_mat_hang",
              label: "Loại mặt hàng",
              as: "select",
              options: itemTypeOptions,
            },
            {
              name: "is_active",
              label: "Trạng thái",
              as: "select",
              options: [
                { value: "", label: "Tất cả" },
                { value: "true", label: "Đang dùng" },
                { value: "false", label: "Ngừng dùng" },
              ],
            },
            {
              name: "sort",
              label: "Sắp xếp",
              as: "select",
              options: [
                { value: "id", label: "ID tăng dần" },
                { value: "ten_mat_hang", label: "Tên mặt hàng" },
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
              label: "Tồn kho",
              numeric: true,
              render: (row) => (
                <>
                  {number(row.so_luong_ton)}
                  <small>{unitLabel(row.don_vi_tinh)}</small>
                </>
              ),
            },
            ...(showPrice
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
              render: (row) => mode === "admin" ? (
                <AdminStatusBadge status={row.is_active ? "hoat_dong" : "bi_khoa"}>
                  {row.is_active ? "Đang dùng" : "Ngừng dùng"}
                </AdminStatusBadge>
              ) : (
                <Badge status={row.is_active ? "hoat_dong" : "bi_khoa"}>
                  {row.is_active ? "Đang dùng" : "Ngừng dùng"}
                </Badge>
              ),
            },
            {
              key: "action",
              label: "Thao tác",
              render: (row) => <Link to={`${base}/${row.id}`}>{readOnly ? "Xem" : "Sửa"} →</Link>,
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
            mode === "admin" ? (
              <InfoGrid
                entries={[
                  ["Mã", snapshot.data.ma_mat_hang],
                  ["Tên mặt hàng", snapshot.data.ten_mat_hang],
                  ["Loại", ITEM_LABELS[snapshot.data.loai_mat_hang]],
                  ["SKU", snapshot.data.sku],
                  ["Đơn vị tính", unitLabel(snapshot.data.don_vi_tinh)],
                  ["Đơn giá", money(snapshot.data.don_gia)],
                  ["Màu sắc", colorLabel(snapshot.data.mau_sac)],
                  ["Mô tả", snapshot.data.mo_ta],
                  ["Trạng thái", snapshot.data.is_active ? "Đang dùng" : "Ngừng dùng"],
                  [
                    "Tồn thực tế",
                    quantity(snapshot.data.so_luong_ton, snapshot.data.don_vi_tinh),
                  ],
                  [
                    "Đang giữ",
                    quantity(snapshot.data.so_luong_dang_giu, snapshot.data.don_vi_tinh),
                  ],
                  [
                    "Còn dùng được",
                    quantity(snapshot.data.so_luong_con_dung, snapshot.data.don_vi_tinh),
                  ],
                  ["Cập nhật tồn", dateTime(snapshot.data.ton_kho_updated_at)],
                ]}
              />
            ) : readOnly ? (
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
  const [values, setValues] = useState({
    ma_mat_hang: record?.ma_mat_hang || "",
    ten_mat_hang: record?.ten_mat_hang || "",
    sku: record?.sku || "",
    loai_mat_hang: record?.loai_mat_hang || ITEM_TYPES[0],
    don_vi_tinh: record?.don_vi_tinh || "cai",
    mau_sac: record?.mau_sac || "",
    mo_ta: record?.mo_ta || "",
    don_gia: record?.don_gia ?? "",
    is_active: record?.is_active ?? true,
  });
  const field = (name) => ({
    value: values[name],
    onChange: (event) => setValues({ ...values, [name]: event.target.value }),
  });
  function submit(event) {
    event.preventDefault();
    const body = {
      ...values,
      ma_mat_hang: values.ma_mat_hang.trim(),
      sku: values.sku.trim(),
      ten_mat_hang: values.ten_mat_hang.trim(),
      mau_sac: nullable(values.mau_sac),
      mo_ta: nullable(values.mo_ta),
      don_gia: Number(values.don_gia),
    };
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
        <Field
          label="Mã mặt hàng"
          pattern="MH-[0-9]{6}"
          placeholder="MH-000001"
          required
          {...field("ma_mat_hang")}
        />
        <Field label="SKU" required {...field("sku")} />
        <Field label="Tên mặt hàng" required {...field("ten_mat_hang")} />
        <Field
          as="select"
          label="Loại mặt hàng"
          required
          options={itemTypeOptions.slice(1)}
          {...field("loai_mat_hang")}
        />
        <Field
          label="Đơn vị tính"
          required
          pattern="[a-z]+(_[a-z]+)*"
          hint="Mã không dấu, ví dụ: cai, chiec, bo."
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
        <Field
          label="Đang sử dụng"
          type="checkbox"
          checked={values.is_active}
          onChange={(event) => setValues({ ...values, is_active: event.target.checked })}
        />
      </div>
      <Field as="textarea" label="Mô tả" rows={3} {...field("mo_ta")} />
      {record && (
        <Notice>
          Tồn hiện tại:{" "}
          <strong>{quantity(record.so_luong_ton, record.don_vi_tinh)}</strong>
          . Không chỉnh số dư tại đây.
        </Notice>
      )}
      <div className="actions actions-end">
        {record && (
          <Button
            variant="secondary"
            disabled={!record.is_active}
            onClick={() =>
              confirm({
                title: "Ngừng sử dụng mặt hàng",
                description: `${record.ma_mat_hang} · ${record.ten_mat_hang}. Mặt hàng ngừng hoạt động không được dùng trong chứng từ mới.`,
                impact:
                  "Giữ nguyên mặt hàng, số dư tồn và chứng từ cũ. Có thể bật lại Đang sử dụng trong hồ sơ mặt hàng.",
                danger: true,
                onConfirm: async () => {
                  await action.mutateAsync({
                    path: `${API.items}/${record.id}`,
                    method: "delete",
                    etag: snapshot.etag,
                  });
                  notify("Đã ngừng sử dụng mặt hàng.");
                },
              })
            }
          >
            Ngừng sử dụng…
          </Button>
        )}
        <Button type="submit" disabled={busy}>
          {busy ? "Đang lưu…" : "Lưu"}
        </Button>
      </div>
    </form>
  );
}
