import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail, useResource } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { dateTime, itemName, money, number, unitLabel } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ApprovalActions } from "../../components/ApprovalActions.jsx";
import { SavedLines, statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { canCreateIssue, issueTypeLabel } from "./issueForm.js";

export function MaterialIssuingPage({ issueType }) {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";
  const [search] = useSearchParams();
  const detail = useDetail(API.issues, id);
  const catalog = useCatalog();
  const base = manager ? "/kho/phieu-xuat" : issueType === "xuat_thanh_pham" ? "/nv/xuat-tp" : "/nv/xuat-nvl";
  const requestId = detail.data?.data.yeu_cau_san_xuat_id || search.get("yeu_cau_san_xuat_id");
  const back = manager ? base : requestId ? `/nv/yeu-cau/${requestId}` : "/nv/yeu-cau";
  if (!manager && !id) return <Navigate to="/nv/yeu-cau" replace />;
  return <>
    <PageHeader title={manager ? "Phiếu xuất kho" : issueTypeLabel(issueType)}
      subtitle={manager ? "Duyệt hoặc từ chối phiếu do nhân viên được giao lập." : "Nội dung phiếu do hệ thống chốt theo yêu cầu sản xuất."} />
    {manager && <IssueList base={base} items={catalog.data?.data || []} />}
    <RecordPanel id={id} query={detail} base={back} title={id === "moi" ? "Lập phiếu xuất" : "Chi tiết phiếu xuất"}>
      {(snapshot) => <QueryState query={catalog}>
        <IssueDetail snapshot={snapshot} items={catalog.data?.data || []} base={base} issueType={issueType} />
      </QueryState>}
    </RecordPanel>
  </>;
}

function IssueList({ base, items }) {
  const collection = useCollection(API.issues, { sort: "-created_at" });
  return <Collection collection={collection} title="Danh sách phiếu xuất" filters={[
    statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"]),
    { name: "loai_phieu", label: "Loại phiếu", as: "select", options: [
      { value: "", label: "Tất cả" },
      { value: "xuat_linh_kien", label: issueTypeLabel("xuat_linh_kien") },
      { value: "xuat_thanh_pham", label: issueTypeLabel("xuat_thanh_pham") },
    ] }, ...dateFilters,
  ]} columns={[
    { key: "ma_phieu_xuat", label: "Mã phiếu", render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_phieu_xuat}</Link> },
    { key: "loai_phieu", label: "Loại", render: (row) => issueTypeLabel(row.loai_phieu) },
    { key: "yeu_cau_san_xuat_id", label: "Yêu cầu", render: (row) => <Link to={`/kho/yeu-cau/${row.yeu_cau_san_xuat_id}`}>YCSX #{row.yeu_cau_san_xuat_id}</Link> },
    { key: "chi_tiet", label: "Mặt hàng", render: (row) => row.chi_tiet.map((line) => itemName(items, line.mat_hang_id)).join(", ") },
    { key: "created_at", label: "Ngày lập", render: (row) => dateTime(row.created_at) },
    { key: "trang_thai", label: "Trạng thái", render: (row) => <Badge status={row.trang_thai} /> },
    { key: "action", label: "Thao tác", render: (row) => <Link to={`${base}/${row.id}`}>Mở →</Link> },
  ]} />;
}

function IssueDetail({ snapshot, items, base, issueType }) {
  const record = snapshot?.data;
  const { user } = useAuth();
  const employee = user.ma_vai_tro === "nhan_vien";
  const [search] = useSearchParams();
  const sourceId = record?.yeu_cau_san_xuat_id || search.get("yeu_cau_san_xuat_id");
  const source = useDetail(API.requests, sourceId);
  const type = record?.loai_phieu || issueType;
  const needsCompletion = !record && type === "xuat_thanh_pham" && source.data?.data.so_luong_can_san_xuat > 0;
  const completion = useResource(`${API.requests}/${sourceId}/chung_tu_hoan_thanh`, {}, Boolean(needsCompletion));
  const { save, busy, error } = useSave();
  const navigate = useNavigate();
  const firstLine = record?.chi_tiet[0];
  const firstItem = items.find((item) => item.id === firstLine?.mat_hang_id);
  if (!record) {
    if (!employee) return <Notice>Chỉ nhân viên được giao yêu cầu được lập phiếu xuất.</Notice>;
    if (!sourceId) return <Notice>Mở yêu cầu được giao để lập phiếu xuất.</Notice>;
    return <QueryState query={source}>
      <ErrorNotice error={error} />
      {needsCompletion && <QueryState query={completion} />}
      <InfoGrid entries={[
        ["Yêu cầu sản xuất", source.data?.data.ma_yeu_cau_san_xuat], ["Loại phiếu", issueTypeLabel(type)],
        ["Thành phẩm", itemName(items, source.data?.data.mat_hang_id)], ["Số lượng yêu cầu", number(source.data?.data.so_luong)],
      ]} />
      <Notice>Nội dung và số lượng phiếu lấy từ nhu cầu đã chốt của yêu cầu. Hệ thống trả chi tiết phiếu sau khi lưu nháp; nhân viên không nhập hoặc sửa từng dòng.</Notice>
      <Button disabled={busy || !canCreateIssue(source.data?.data, type, user.id, completion.data?.data)}
        onClick={() => save({ path: API.issues, method: "post", versioned: false,
          body: { loai_phieu: type, yeu_cau_san_xuat_id: Number(sourceId) } },
        (result) => navigate(`${base}/${result.data.id}`))}>Lưu nháp</Button>
    </QueryState>;
  }
  return <div className="stack">
    <h3>{record.ma_phieu_xuat}</h3>
    <InfoGrid entries={[
      ["Mã phiếu xuất", record.ma_phieu_xuat], ["Trạng thái", <Badge status={record.trang_thai} />],
      ["Yêu cầu sản xuất", <Link to={`/${employee ? "nv" : "kho"}/yeu-cau/${sourceId}`}>YCSX #{sourceId}</Link>],
      ["Ngày lập", dateTime(record.created_at)],
      [type === "xuat_linh_kien" ? "Mặt hàng đầu" : "Mã thành phẩm", firstItem?.sku || firstItem?.ma_mat_hang || "—"],
      ["Số lượng xuất", record.chi_tiet.length === 1 ? `${number(firstLine.so_luong)} ${unitLabel(firstItem?.don_vi_tinh) || ""}` : `${record.chi_tiet.length} dòng mặt hàng`],
      ["Loại phiếu", issueTypeLabel(type)], ["Tổng tiền server chốt", money(record.tong_tien)],
      ...(record.ly_do_tu_choi ? [["Lý do từ chối", record.ly_do_tu_choi]] : []),
    ]} />
    <SavedLines lines={record.chi_tiet} items={items} prices />
    <Notice>Gửi hoặc gửi lại chưa trừ tồn; hàng vẫn được giữ cho yêu cầu. Quản lý kho duyệt phiếu để ghi xuất kho.</Notice>
    <QueryState query={source}>
      <ApprovalActions kind="issue" path={API.issues} snapshot={snapshot} items={items}
        assignedId={source.data?.data.nhan_vien_duoc_giao_id} />
    </QueryState>
  </div>;
}
