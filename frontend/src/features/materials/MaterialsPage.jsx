import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { ITEM_LABELS, money, nullable, number, dateTime } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Field } from "../../components/Field.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ErrorNotice, Notice } from "../../components/QueryState.jsx";
import { itemTypeOptions } from "../../components/ResourceFields.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
export function MaterialsPage({ readOnly = false }) {
  const base = readOnly ? "/nv/ton-kho" : "/kho/mat-hang";
  const { id } = useParams();
  const collection = useCollection(API.items, { sort: "id" });
  const detail = useDetail(API.items, id);
  return (
    <>
      <PageHeader
        title={readOnly ? "Tra cứu tồn kho" : "Mặt hàng và tồn kho"}
        subtitle="NVL · Linh kiện · Bán thành phẩm · Thành phẩm. Tồn kho chỉ thay đổi qua chứng từ đã ghi sổ."
        action={
          !readOnly && (
            <Link className="btn btn-primary" to={`${base}/moi`}>
              Thêm mặt hàng
            </Link>
          )
        }
      />
      {readOnly && (
        <Notice>
          Số lượng tồn được đọc từ dữ liệu mặt hàng. Nhân viên chỉ xem, không thể chỉnh sửa trực tiếp tồn kho.
        </Notice>
      )}
      <div>
        <Collection
          collection={collection}
          title={readOnly ? "Danh sách tồn kho" : "Danh sách"}
          searchPlaceholder={readOnly ? "Tìm mã hoặc tên mặt hàng…" : undefined}
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
                { value: "true", label: "Đang sử dụng" },
                { value: "false", label: "Ngừng sử dụng" },
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
              label: readOnly ? "Mã hàng / SKU" : "Mã",
              render: (row) => readOnly ? (
                <>
                  <Link to={`${base}/${row.id}`}>{row.sku}</Link>
                  <small>{row.ma_mat_hang}</small>
                </>
              ) : <Link to={`${base}/${row.id}`}>{row.ma_mat_hang}</Link>,
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
            ...(!readOnly ? [{ key: "sku", label: "SKU" }] : []),
            ...(readOnly ? [{ key: "loai_mat_hang", label: "Loại", render: (row) => ITEM_LABELS[row.loai_mat_hang] }] : []),
            {
              key: "so_luong_ton",
              label: "Tồn kho",
              numeric: true,
              render: (row) => (
                <>
                  {number(row.so_luong_ton)}
                  <small>{row.don_vi_tinh}</small>
                </>
              ),
            },
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
              render: (row) => (
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
            readOnly ? (
              <InfoGrid
                entries={[
                  ["Mã hàng", snapshot?.data.sku],
                  ["Loại hàng", ITEM_LABELS[snapshot?.data.loai_mat_hang]],
                  ["Tồn kho hiện tại", `${number(snapshot?.data.so_luong_ton)} ${snapshot?.data.don_vi_tinh || ""}`],
                  ["Tên mặt hàng", snapshot?.data.ten_mat_hang],
                  ["Mã nội bộ", snapshot?.data.ma_mat_hang],
                  ["Đơn vị tính", snapshot?.data.don_vi_tinh],
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
    loai_mat_hang: record?.loai_mat_hang || "nguyen_vat_lieu",
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
          <strong>
            {number(record.so_luong_ton)} {record.don_vi_tinh}
          </strong>
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
