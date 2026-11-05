import { Link, useParams, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider.jsx";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail, useWrite } from "../../lib/api/useResources.js";
import { dateTime, itemName } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { Notice } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
const base = "/kho/ticket";
export function TicketsPage() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const collection = useCollection(API.tickets, {
    sort: "-created_at",
    phieu_nhap_id: search.get("phieu_nhap_id") || "",
  });
  const detail = useDetail(API.tickets, id);
  const catalog = useCatalog();
  return (
    <>
      <PageHeader
        title="Ticket sự cố"
        subtitle="Theo dõi lỗi điều chỉnh phiếu nhập. Đóng ticket không làm thay đổi tồn kho."
        action={
          <Button reason="Ticket chỉ được sinh tự động khi xác nhận điều chỉnh thất bại theo nghiệp vụ.">
            Tạo ticket
          </Button>
        }
      />
      <Collection
        collection={collection}
        search={false}
        filters={[
          statusFilter(["cho_xu_ly", "dang_xu_ly", "da_xu_ly"]),
          { name: "phieu_nhap_id", label: "ID phiếu nhập", type: "number", min: 1, step: 1 },
          ...dateFilters,
        ]}
        columns={[
          {
            key: "ma_ticket",
            label: "Mã ticket",
            render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_ticket}</Link>,
          },
          {
            key: "phieu_nhap_id",
            label: "Phiếu nhập",
            render: (row) => (
              <Link to={`/kho/phieu-nhap/${row.phieu_nhap_id}`}>#{row.phieu_nhap_id}</Link>
            ),
          },
          { key: "mo_ta_loi", label: "Mô tả sự cố" },
          { key: "created_at", label: "Tạo lúc", render: (row) => dateTime(row.created_at) },
          {
            key: "trang_thai",
            label: "Trạng thái",
            render: (row) => <Badge status={row.trang_thai} />,
          },
          {
            key: "action",
            label: "Thao tác",
            render: (row) => <Link to={`${base}/${row.id}`}>Xử lý →</Link>,
          },
        ]}
      />
      <RecordPanel id={id} query={detail} base={base} title="Chi tiết ticket">
        {(snapshot) =>
          snapshot && <TicketDetail snapshot={snapshot} items={catalog.data?.data || []} />
        }
      </RecordPanel>
    </>
  );
}
function TicketDetail({ snapshot, items }) {
  const record = snapshot.data;
  const { user } = useAuth();
  const { confirm, notify } = useFeedback();
  const mutation = useWrite();
  function action(resolve = false) {
    confirm({
      title: resolve ? "Giải quyết ticket" : "Nhận xử lý ticket",
      description: `${record.ma_ticket} · phiếu nhập #${record.phieu_nhap_id}.`,
      reason: resolve,
      reasonLabel: "Kết quả xử lý",
      impact:
        "Chỉ cập nhật trạng thái và kết quả ticket; không thay đổi số dư kho hoặc tự xác nhận phiếu điều chỉnh.",
      onConfirm: async (result) => {
        await mutation.mutateAsync({
          path: `${API.tickets}/${record.id}/${resolve ? "giai_quyet" : "nhan_xu_ly"}`,
          body: resolve ? { ket_qua_xu_ly: result } : {},
          etag: snapshot.etag,
        });
        notify("Đã cập nhật ticket.");
      },
    });
  }
  return (
    <div className="stack">
      <div className="actions">
        <h3>{record.ma_ticket}</h3>
        <Badge status={record.trang_thai} />
      </div>
      <InfoGrid
        entries={[
          [
            "Phiếu nhập",
            <Link to={`/kho/phieu-nhap/${record.phieu_nhap_id}`}>#{record.phieu_nhap_id}</Link>,
          ],
          ["Người tạo", `Nhân viên #${record.nguoi_tao_id}`],
          [
            "Người xử lý",
            record.nguoi_xu_ly_id ? `Nhân viên #${record.nguoi_xu_ly_id}` : "Chưa nhận",
          ],
          ["Tạo lúc", dateTime(record.created_at)],
          ["Đóng lúc", dateTime(record.closed_at)],
        ]}
      />
      <Notice tone="warning">{record.mo_ta_loi}</Notice>
      <DataTable
        rows={record.chi_tiet}
        columns={[
          {
            key: "mat_hang_id",
            label: "Mặt hàng",
            render: (line) => itemName(items, line.mat_hang_id),
          },
          { key: "so_luong_hieu_luc_truoc", label: "Lượng trước", numeric: true },
          { key: "so_luong_de_nghi", label: "Đề nghị", numeric: true },
          { key: "so_luong_bien_dong", label: "Biến động", numeric: true },
          { key: "ton_kho_tai_thoi_diem", label: "Tồn khi lỗi", numeric: true },
        ]}
      />
      {record.ket_qua_xu_ly && (
        <Notice>
          <strong>Kết quả xử lý:</strong> {record.ket_qua_xu_ly}
        </Notice>
      )}
      <div className="actions actions-end">
        {record.trang_thai === "cho_xu_ly" && <Button onClick={() => action()}>Nhận xử lý</Button>}
        {record.trang_thai === "dang_xu_ly" && (
          <Button
            reason={
              record.nguoi_xu_ly_id !== user.id ? "Ticket đang được quản lý khác xử lý." : undefined
            }
            onClick={() => action(true)}
          >
            Giải quyết
          </Button>
        )}
      </div>
    </div>
  );
}
