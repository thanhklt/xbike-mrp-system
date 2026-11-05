import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import {
  useCatalog,
  useChoices,
  useCollection,
  useDetail,
  useWrite,
} from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { today, dateTime, money, nullable } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import {
  DocumentLines,
  newLine,
  linePayload,
  SavedLines,
  statusFilter,
  dateFilters,
} from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
const base = "/kho/phieu-nhap";
export function ReceivingPage() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const collection = useCollection(API.receipts, {
    sort: "-created_at",
    ncc_id: search.get("ncc_id") || "",
  });
  const detail = useDetail(API.receipts, id);
  const catalog = useCatalog();
  const suppliers = useChoices(API.suppliers);
  const items = catalog.data?.data || [];
  return (
    <>
      <PageHeader
        title="Phiếu nhập kho"
        subtitle="Phiếu nháp không cộng tồn. Chỉ hoàn tất nhập kho mới ghi sổ."
        action={
          <Link className="btn btn-primary" to={`${base}/moi`}>
            Tạo phiếu nhập
          </Link>
        }
      />
      <div className="stack">
        <Collection
          collection={collection}
          filters={[statusFilter(["nhap", "hoan_thanh"]), ...dateFilters]}
          columns={[
            {
              key: "ma_phieu_nhap",
              label: "Mã phiếu",
              render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_phieu_nhap}</Link>,
            },
            {
              key: "ncc_id",
              label: "Nhà cung cấp",
              render: (row) =>
                suppliers.data?.find((supplier) => supplier.id === row.ncc_id)?.ten_ncc ||
                `NCC #${row.ncc_id}`,
            },
            { key: "ngay_nhap", label: "Ngày nhập" },
            {
              key: "tong_tien",
              label: "Tổng tiền",
              numeric: true,
              render: (row) => money(row.tong_tien),
            },
            {
              key: "trang_thai",
              label: "Trạng thái",
              render: (row) => <Badge status={row.trang_thai} />,
            },
            {
              key: "action",
              label: "Thao tác",
              render: (row) => (
                <Link to={`${base}/${row.id}`}>
                  {row.trang_thai === "nhap" ? "Mở nháp" : "Xem"} →
                </Link>
              ),
            },
          ]}
        />
        <RecordPanel
          id={id}
          query={detail}
          base={base}
          title={id === "moi" ? "Tạo phiếu nhập" : "Chi tiết phiếu nhập"}
        >
          {(snapshot) => (
            <QueryState query={catalog}>
              <ReceiptEditor snapshot={snapshot} items={items} suppliers={suppliers} />
            </QueryState>
          )}
        </RecordPanel>
      </div>
    </>
  );
}
function ReceiptEditor({ snapshot, items, suppliers }) {
  const record = snapshot?.data;
  const editable = !record || record.trang_thai === "nhap";
  const navigate = useNavigate();
  const { confirm, notify } = useFeedback();
  const action = useWrite();
  const { save, busy, error } = useSave();
  const initial = {
    ncc_id: String(record?.ncc_id || ""),
    ngay_nhap: record?.ngay_nhap || today(),
    ghi_chu: record?.ghi_chu || "",
  };
  const [values, setValues] = useState(initial);
  const [lines, setLines] = useState(
    () =>
      record?.chi_tiet.map((line) =>
        newLine({
          ...line,
          mat_hang_id: String(line.mat_hang_id),
          so_luong: String(line.so_luong),
          don_gia_thuc: String(line.don_gia_thuc ?? 0),
        }),
      ) || [newLine()],
  );
  const dirty =
    JSON.stringify(values) !== JSON.stringify(initial) ||
    Boolean(
      record &&
      JSON.stringify(linePayload(lines, true)) !==
        JSON.stringify(
          record.chi_tiet.map(({ mat_hang_id, so_luong, don_gia_thuc }) => ({
            mat_hang_id,
            so_luong,
            don_gia_thuc,
          })),
        ),
    );
  function submit(event) {
    event.preventDefault();
    const body = {
      ncc_id: Number(values.ncc_id),
      ngay_nhap: values.ngay_nhap,
      ghi_chu: nullable(values.ghi_chu),
      chi_tiet: linePayload(lines, true),
    };
    save(
      {
        path: record ? `${API.receipts}/${record.id}` : API.receipts,
        method: record ? "patch" : "post",
        body,
        versioned: Boolean(record),
        etag: snapshot?.etag,
      },
      (result) => navigate(`${base}/${result.data.id}`),
    );
  }
  function confirmAction(remove = false) {
    confirm({
      title: remove ? "Xóa phiếu nhập nháp" : "Hoàn tất nhập kho",
      description: `${record.ma_phieu_nhap} · ngày nhập ${record.ngay_nhap}.`,
      content: <SavedLines lines={record.chi_tiet} items={items} prices />,
      danger: remove,
      impact: remove
        ? "Xóa bản nháp, không thay đổi tồn kho."
        : "Cộng số lượng từng mặt hàng vào kho và ghi giao dịch một lần. Phiếu hoàn tất không sửa/xóa trực tiếp.",
      onConfirm: async () => {
        const result = await action.mutateAsync({
          path: `${API.receipts}/${record.id}${remove ? "" : "/hoan_tat"}`,
          method: remove ? "delete" : "post",
          etag: snapshot.etag,
        });
        notify(
          remove
            ? "Đã xóa phiếu nhập nháp."
            : `Đã hoàn tất nhập kho.${result.data?.giao_dich_kho_ids?.length ? ` Giao dịch nhập gốc: ${result.data.giao_dich_kho_ids.join(", ")}.` : ""}`,
        );
        if (remove) navigate(base);
      },
    });
  }
  return (
    <div className="stack">
      {record && (
        <div className="actions">
          <h3>{record.ma_phieu_nhap}</h3>
          <Badge status={record.trang_thai} />
        </div>
      )}
      <ErrorNotice error={error} />
      {editable ? (
        <QueryState query={suppliers}>
          <form className="stack" onSubmit={submit}>
            <div className="form-grid">
              <Field
                as="select"
                label="Nhà cung cấp"
                required
                value={values.ncc_id}
                onChange={(event) => setValues({ ...values, ncc_id: event.target.value })}
              >
                <option value="">Chọn nhà cung cấp</option>
                {suppliers.data?.map((supplier) => (
                  <option key={supplier.id} value={supplier.id}>
                    {supplier.ma_ncc} · {supplier.ten_ncc}
                  </option>
                ))}
              </Field>
              <Field
                label="Ngày nhập"
                type="date"
                required
                value={values.ngay_nhap}
                onChange={(event) => setValues({ ...values, ngay_nhap: event.target.value })}
              />
            </div>
            <Field
              as="textarea"
              rows={2}
              label="Ghi chú"
              value={values.ghi_chu}
              onChange={(event) => setValues({ ...values, ghi_chu: event.target.value })}
            />
            <DocumentLines
              lines={lines}
              onChange={setLines}
              items={items}
              prices
              types={["nguyen_vat_lieu", "linh_kien"]}
            />
            <div className="actions actions-end">
              <span className="muted">
                Tạm tính:{" "}
                {money(
                  lines.reduce(
                    (sum, line) => sum + Number(line.so_luong) * Number(line.don_gia_thuc),
                    0,
                  ),
                )}
              </span>
              <Button type="submit" disabled={busy}>
                Lưu nháp
              </Button>
            </div>
          </form>
        </QueryState>
      ) : (
        <>
          <InfoGrid
            entries={[
              ["Ngày nhập", record.ngay_nhap],
              ["Người lập", `Nhân viên #${record.nhan_vien_id}`],
              ["Tổng tiền", money(record.tong_tien)],
              ["Tạo lúc", dateTime(record.created_at)],
              ["Ghi chú", record.ghi_chu],
            ]}
          />
          <SavedLines lines={record.chi_tiet} items={items} prices />
          <Notice>
            Phiếu đã hoàn tất, nội dung bất biến. Sai số lượng cần lập phiếu điều chỉnh.
          </Notice>
          <div className="actions">
            <Link className="btn btn-primary" to={`/kho/dieu-chinh/moi?phieu_nhap_id=${record.id}`}>
              Tạo phiếu điều chỉnh
            </Link>
            <Button
              variant="secondary"
              reason="Ticket chỉ được sinh khi xác nhận điều chỉnh thất bại theo nghiệp vụ."
            >
              Tạo ticket sự cố
            </Button>
          </div>
        </>
      )}
      {record && editable && (
        <div className="actions actions-end">
          <Button
            variant="secondary"
            reason={dirty ? "Lưu hoặc tải lại bản nháp trước khi xóa." : undefined}
            onClick={() => confirmAction(true)}
          >
            Xóa nháp
          </Button>
          <Button
            reason={dirty ? "Lưu hoặc tải lại bản nháp trước khi hoàn tất." : undefined}
            onClick={() => confirmAction()}
          >
            Hoàn tất nhập kho
          </Button>
        </div>
      )}
    </div>
  );
}
