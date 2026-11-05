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
import { itemName, dateTime } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { Badge } from "../../components/Badge.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { SavedLines, statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
const base = "/kho/dieu-chinh";
export function AdjustmentsPage() {
  const { id } = useParams();
  const collection = useCollection(API.adjustments, { sort: "-created_at" });
  const detail = useDetail(API.adjustments, id);
  const catalog = useCatalog();
  return (
    <>
      <PageHeader
        title="Điều chỉnh kho"
        subtitle="Sửa sai số lượng của phiếu nhập đã hoàn tất. Một bước xác nhận, không có luồng gửi/duyệt riêng."
        action={
          <Link className="btn btn-primary" to={`${base}/moi`}>
            Tạo phiếu điều chỉnh
          </Link>
        }
      />
      <Collection
        collection={collection}
        filters={[statusFilter(["nhap", "da_xac_nhan", "loi"]), ...dateFilters]}
        columns={[
          {
            key: "ma_phieu",
            label: "Mã phiếu",
            render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_phieu}</Link>,
          },
          {
            key: "phieu_nhap_id",
            label: "Phiếu nhập",
            render: (row) => (
              <Link to={`/kho/phieu-nhap/${row.phieu_nhap_id}`}>#{row.phieu_nhap_id}</Link>
            ),
          },
          { key: "ly_do", label: "Lý do" },
          { key: "created_at", label: "Tạo lúc", render: (row) => dateTime(row.created_at) },
          {
            key: "trang_thai",
            label: "Trạng thái",
            render: (row) => <Badge status={row.trang_thai} />,
          },
          {
            key: "action",
            label: "Thao tác",
            render: (row) => <Link to={`${base}/${row.id}`}>Mở →</Link>,
          },
        ]}
      />
      <RecordPanel
        id={id}
        query={detail}
        base={base}
        title={id === "moi" ? "Tạo phiếu điều chỉnh" : "Chi tiết điều chỉnh"}
      >
        {(snapshot) => <AdjustmentEditor snapshot={snapshot} items={catalog.data?.data || []} />}
      </RecordPanel>
    </>
  );
}
function adjustmentLine(line = {}) {
  return {
    key: crypto.randomUUID(),
    giao_dich_goc_id: String(line.giao_dich_goc_id || ""),
    so_luong_dung: String(line.so_luong_dung ?? ""),
  };
}
function adjustmentPayload(lines) {
  return lines.map(({ giao_dich_goc_id, so_luong_dung }) => ({
    giao_dich_goc_id: Number(giao_dich_goc_id),
    so_luong_dung: Number(so_luong_dung),
  }));
}
function AdjustmentEditor({ snapshot, items }) {
  const record = snapshot?.data;
  const [search] = useSearchParams();
  const [receiptId, setReceiptId] = useState(
    String(record?.phieu_nhap_id || search.get("phieu_nhap_id") || ""),
  );
  const [reason, setReason] = useState(record?.ly_do || "");
  const [lines, setLines] = useState(
    () => record?.chi_tiet.map(adjustmentLine) || [adjustmentLine()],
  );
  const editable = !record || record.trang_thai === "nhap";
  const receipts = useChoices(API.receipts, { trang_thai: "hoan_thanh" }, !record);
  const receipt = useDetail(API.receipts, receiptId);
  const navigate = useNavigate();
  const { save, busy, error } = useSave();
  const mutation = useWrite();
  const { confirm, notify } = useFeedback();
  const dirty = Boolean(
    record &&
    (reason !== record.ly_do ||
      JSON.stringify(adjustmentPayload(lines)) !==
        JSON.stringify(
          record.chi_tiet.map(({ giao_dich_goc_id, so_luong_dung }) => ({
            giao_dich_goc_id,
            so_luong_dung,
          })),
        )),
  );
  function submit(event) {
    event.preventDefault();
    const body = {
      ly_do: reason.trim(),
      chi_tiet: adjustmentPayload(lines),
      ...(!record ? { phieu_nhap_id: Number(receiptId) } : {}),
    };
    save(
      {
        path: record ? `${API.adjustments}/${record.id}` : API.adjustments,
        method: record ? "patch" : "post",
        body,
        versioned: Boolean(record),
        etag: snapshot?.etag,
      },
      (result) => navigate(`${base}/${result.data.id}`),
    );
  }
  function act(remove = false) {
    confirm({
      title: remove ? "Xóa phiếu điều chỉnh nháp" : "Xác nhận điều chỉnh kho",
      description: `${record.ma_phieu} · phiếu nhập #${record.phieu_nhap_id}.`,
      content: <AdjustmentLines lines={record.chi_tiet} items={items} />,
      danger: true,
      impact: remove
        ? "Xóa nháp không thay đổi tồn."
        : "Backend kiểm tra lượng hiệu lực của nguồn và tồn hiện tại, ghi toàn bộ chênh lệch hoặc không ghi dòng nào. Chỉ lỗi thiếu tồn đủ điều kiện mới sinh ticket.",
      onConfirm: async () => {
        const result = await mutation.mutateAsync({
          path: `${API.adjustments}/${record.id}${remove ? "" : "/xac_nhan"}`,
          method: remove ? "delete" : "post",
          etag: snapshot.etag,
        });
        notify(
          remove
            ? "Đã xóa nháp."
            : `Đã xác nhận điều chỉnh.${result.data?.giao_dich_kho_ids?.length ? ` Giao dịch kho: ${result.data.giao_dich_kho_ids.join(", ")}.` : ""}`,
        );
        if (remove) navigate(base);
      },
    });
  }
  return (
    <div className="stack">
      {record && (
        <>
          <div className="actions">
            <h3>{record.ma_phieu}</h3>
            <Badge status={record.trang_thai} />
          </div>
          <InfoGrid
            entries={[
              [
                "Phiếu nhập",
                <Link to={`/kho/phieu-nhap/${record.phieu_nhap_id}`}>#{record.phieu_nhap_id}</Link>,
              ],
              ["Xác nhận lúc", dateTime(record.confirmed_at)],
            ]}
          />
        </>
      )}
      <ErrorNotice error={error} />
      {editable ? (
        <form className="stack" onSubmit={submit}>
          {!record && (
            <QueryState query={receipts}>
              <Field
                as="select"
                label="Phiếu nhập đã hoàn tất"
                required
                value={receiptId}
                onChange={(event) => {
                  setReceiptId(event.target.value);
                  setLines([adjustmentLine()]);
                }}
              >
                <option value="">Chọn phiếu nhập</option>
                {receipts.data?.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.ma_phieu_nhap} · {entry.ngay_nhap}
                  </option>
                ))}
              </Field>
            </QueryState>
          )}
          {receiptId && (
            <QueryState query={receipt}>
              <SavedLines lines={receipt.data?.data.chi_tiet || []} items={items} />
            </QueryState>
          )}
          <Field
            as="textarea"
            label="Lý do điều chỉnh"
            rows={3}
            required
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <Notice tone="warning">
            Nhập ID giao dịch nhập gốc và số lượng đúng của từng dòng. Hiện chưa hỗ trợ tự tra/chọn
            giao dịch từ sổ kho; không dùng ID dòng phiếu nhập thay cho ID giao dịch. Server kiểm
            tra giao dịch có thuộc phiếu nhập đã chọn.
          </Notice>
          <div className="table-scroll">
            <table className="line-editor">
              <thead>
                <tr>
                  <th>ID giao dịch nhập gốc</th>
                  <th>Số lượng đúng</th>
                  <th>Xóa</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => (
                  <tr key={line.key}>
                    <td>
                      <input
                        aria-label={`ID giao dịch gốc dòng ${index + 1}`}
                        required
                        type="number"
                        min="1"
                        max="2147483647"
                        step="1"
                        value={line.giao_dich_goc_id}
                        onChange={(event) =>
                          setLines(
                            lines.map((entry) =>
                              entry.key === line.key
                                ? { ...entry, giao_dich_goc_id: event.target.value }
                                : entry,
                            ),
                          )
                        }
                      />
                    </td>
                    <td>
                      <input
                        aria-label={`Số lượng đúng dòng ${index + 1}`}
                        required
                        type="number"
                        min="0"
                        max="2147483647"
                        step="1"
                        value={line.so_luong_dung}
                        onChange={(event) =>
                          setLines(
                            lines.map((entry) =>
                              entry.key === line.key
                                ? { ...entry, so_luong_dung: event.target.value }
                                : entry,
                            ),
                          )
                        }
                      />
                    </td>
                    <td>
                      <Button
                        variant="secondary"
                        aria-label={`Xóa dòng ${index + 1}`}
                        disabled={lines.length === 1}
                        onClick={() => setLines(lines.filter((entry) => entry.key !== line.key))}
                      >
                        ×
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="actions">
            <Button variant="secondary" onClick={() => setLines([...lines, adjustmentLine()])}>
              + Thêm dòng
            </Button>
            <Button type="submit" disabled={busy}>
              Lưu nháp
            </Button>
          </div>
        </form>
      ) : (
        <>
          <Notice>{record.ly_do}</Notice>
          <AdjustmentLines lines={record.chi_tiet} items={items} />
        </>
      )}
      {record && editable && (
        <div className="actions actions-end">
          <Button
            variant="secondary"
            reason={dirty ? "Lưu hoặc tải lại bản nháp trước." : undefined}
            onClick={() => act(true)}
          >
            Xóa nháp
          </Button>
          <Button
            reason={dirty ? "Lưu hoặc tải lại bản nháp trước khi xác nhận." : undefined}
            onClick={() => act()}
          >
            Xác nhận điều chỉnh
          </Button>
        </div>
      )}
      {record && (
        <Link to={`/kho/ticket?phieu_nhap_id=${record.phieu_nhap_id}`}>
          Xem ticket của phiếu nhập →
        </Link>
      )}
    </div>
  );
}
function AdjustmentLines({ lines, items }) {
  return (
    <DataTable
      rows={lines}
      columns={[
        {
          key: "mat_hang_id",
          label: "Mặt hàng",
          render: (line) => itemName(items, line.mat_hang_id),
        },
        { key: "giao_dich_goc_id", label: "Giao dịch gốc" },
        { key: "so_luong_hieu_luc_truoc", label: "Lượng nguồn trước", numeric: true },
        { key: "so_luong_dung", label: "Số lượng đúng", numeric: true },
        { key: "so_luong_bien_dong", label: "Biến động", numeric: true },
      ]}
    />
  );
}
