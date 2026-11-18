import { useEffect } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail, useResource } from "../../lib/api/useResources.js";
import { useSave } from "../../lib/useSave.js";
import { dateTime, itemDisplayName, money, number, unitLabel } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { Button } from "../../components/Button.jsx";
import { ApprovalActions } from "../../components/ApprovalActions.jsx";
import { SavedLines, statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { dateRangeError } from "../../components/filterFields.js";
import { ErrorNotice, Notice, QueryState } from "../../components/QueryState.jsx";
import { canCreateIssue, issueTypeLabel } from "./issueForm.js";

const managerBase = "/kho/phieu-xuat";
const issueLabel = (value) => (value === "xuat_thanh_pham" ? "Thành phẩm" : "Linh kiện");

export function MaterialIssuingPage({ issueType }) {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";

  if (manager && id === "moi") return <Navigate to={managerBase} replace />;
  if (!manager && !id) return <Navigate to="/nv/yeu-cau" replace />;
  return manager ? <ManagerIssuePage id={id} /> : <EmployeeIssuePage id={id} issueType={issueType} />;
}

// UC-34–40: QLK reads/reviews source-generated issue documents, without editing their lines.
function ManagerIssuePage({ id }) {
  const collection = useCollection(API.issues, { sort: "-created_at" });
  const detail = useDetail(API.issues, id);
  const catalog = useCatalog();
  return (
    <>
      <PageHeader
        title="Phiếu xuất kho"
        subtitle="Theo dõi, duyệt và từ chối phiếu xuất linh kiện, thành phẩm. Chỉ duyệt mới trừ tồn; nhân viên được giao lập phiếu từ yêu cầu."
      />
      <Collection
        collection={collection}
        allowReset
        pageSizes={[20, 50, 100]}
        validate={dateRangeError}
        filters={[
          statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"]),
          {
            name: "loai_phieu",
            label: "Loại phiếu",
            as: "select",
            options: [
              { value: "", label: "Tất cả" },
              { value: "xuat_linh_kien", label: "Xuất linh kiện" },
              { value: "xuat_thanh_pham", label: "Xuất thành phẩm" },
            ],
          },
          ...dateFilters,
        ]}
        columns={[
          {
            key: "ma_phieu_xuat",
            label: "Mã phiếu",
            render: (row) => <Link to={`${managerBase}/${row.id}`}>{row.ma_phieu_xuat}</Link>,
          },
          { key: "loai_phieu", label: "Loại", render: (row) => issueLabel(row.loai_phieu) },
          { key: "created_at", label: "Tạo lúc", render: (row) => dateTime(row.created_at) },
          {
            key: "trang_thai",
            label: "Trạng thái",
            render: (row) => <Badge status={row.trang_thai} />,
          },
          {
            key: "action",
            label: "Thao tác",
            render: (row) => <Link to={`${managerBase}/${row.id}`}>Mở →</Link>,
          },
        ]}
      />
      <RecordPanel id={id} query={detail} base={managerBase} title="Chi tiết phiếu xuất">
        {(snapshot) => (
          <QueryState query={catalog}>
            <ManagerIssueDetail snapshot={snapshot} items={catalog.data?.data || []} />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}

function ManagerIssueDetail({ snapshot, items }) {
  const record = snapshot.data;
  const creator = useDetail(API.employees, record.nhan_vien_id);
  const source = useDetail(API.requests, record.yeu_cau_san_xuat_id);
  return (
    <div className="stack">
      <div className="actions">
        <h3>{record.ma_phieu_xuat}</h3>
        <Badge status={record.trang_thai} />
      </div>
      <InfoGrid
        entries={[
          [
            "Người lập",
            <QueryState query={creator}>{creator.data?.data.ho_ten || "Chưa có họ tên"}</QueryState>,
          ],
          ["Tạo lúc", dateTime(record.created_at)],
          ["Loại phiếu", issueLabel(record.loai_phieu)],
          [
            "Nguồn",
            <QueryState query={source}>{source.data?.data.ma_yeu_cau_san_xuat}</QueryState>,
          ],
          ["Tổng tiền đã chốt", money(record.tong_tien)],
          ["Lý do từ chối", record.ly_do_tu_choi],
        ]}
      />
      <SavedLines lines={record.chi_tiet} items={items} prices />
      <ApprovalActions
        kind="issue"
        path={API.issues}
        base={managerBase}
        snapshot={snapshot}
        items={items}
        allowedActions={{
          approve: record.trang_thai === "cho_duyet",
          reject: record.trang_thai === "cho_duyet",
        }}
      />
    </div>
  );
}

function EmployeeIssuePage({ id, issueType }) {
  const [search] = useSearchParams();
  const detail = useDetail(API.issues, id);
  const catalog = useCatalog();
  const base = issueType === "xuat_thanh_pham" ? "/nv/xuat-tp" : "/nv/xuat-nvl";
  const requestId = detail.data?.data.yeu_cau_san_xuat_id || search.get("yeu_cau_san_xuat_id");
  const back = requestId ? `/nv/yeu-cau/${requestId}` : "/nv/yeu-cau";
  return (
    <>
      <PageHeader
        title={issueTypeLabel(issueType)}
        subtitle="Nội dung phiếu do hệ thống chốt theo yêu cầu sản xuất."
      />
      <RecordPanel
        id={id}
        query={detail}
        base={back}
        title={id === "moi" ? "Lập phiếu xuất" : "Chi tiết phiếu xuất"}
      >
        {(snapshot) => (
          <QueryState query={catalog}>
            <EmployeeIssueDetail
              snapshot={snapshot}
              items={catalog.data?.data || []}
              base={base}
              issueType={issueType}
            />
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}

function EmployeeIssueDetail({ snapshot, items, base, issueType }) {
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
  const existing = useResource(`${API.issues}/theo_yeu_cau/${sourceId}`, {}, Boolean(!record && employee && sourceId));
  const existingIssue = existing.data?.data.find((issue) => issue.loai_phieu === type);
  const eligible = canCreateIssue(source.data?.data, type, user.id, completion.data?.data);
  const preview = useResource(`${API.issues}/xem_truoc/${sourceId}`, { loai_phieu: type },
    Boolean(!record && employee && sourceId && existing.isSuccess && !existingIssue && eligible));
  const { refetch: reloadExisting } = existing;
  const { refetch: reloadSource } = source;
  useEffect(() => {
    if (error?.status === 409 || preview.error?.status === 409) {
      reloadExisting();
      reloadSource();
    }
  }, [error, preview.error, reloadExisting, reloadSource]);
  const navigate = useNavigate();
  const firstLine = record?.chi_tiet[0];
  const firstItem = items.find((item) => item.id === firstLine?.mat_hang_id);
  if (!record) {
    if (!employee) return <Notice>Chỉ nhân viên được giao yêu cầu được lập phiếu xuất.</Notice>;
    if (!sourceId) return <Notice>Mở yêu cầu được giao để lập phiếu xuất.</Notice>;
    return <QueryState query={source}><QueryState query={existing}>
      <ErrorNotice error={error} />
      {needsCompletion && <QueryState query={completion} />}
      <InfoGrid entries={[
        ["Yêu cầu sản xuất", source.data?.data?.ma_yeu_cau_san_xuat || (source.isPending ? "Đang tải…" : "Yêu cầu sản xuất")], ["Loại phiếu", issueTypeLabel(type)],
        ["Thành phẩm", itemDisplayName(items, source.data?.data?.mat_hang_id)], ["Số lượng yêu cầu", number(source.data?.data?.so_luong)],
      ]} />
      {existingIssue ? <Link className="btn btn-secondary" to={`${base}/${existingIssue.id}`}>Mở phiếu {existingIssue.ma_phieu_xuat}</Link> : <>
      {eligible && <QueryState query={preview}><SavedLines lines={preview.data?.data.chi_tiet || []} items={items} units /></QueryState>}
      <Button disabled={busy || !eligible || !preview.isSuccess || preview.isFetching}
        onClick={() => save({ path: API.issues, method: "post", versioned: false,
          body: { loai_phieu: type, yeu_cau_san_xuat_id: Number(sourceId) } },
        (result) => navigate(`${base}/${result.data.id}`))}>Lưu nháp</Button>
      </>}
    </QueryState></QueryState>;
  }
  return <div className="stack">
    <h3>{record.ma_phieu_xuat}</h3>
    <InfoGrid entries={[
      ["Mã phiếu xuất", record.ma_phieu_xuat], ["Trạng thái", <Badge status={record.trang_thai} />],
      ["Yêu cầu sản xuất", <Link to={`/${employee ? "nv" : "kho"}/yeu-cau/${sourceId}`}>{source.data?.data?.ma_yeu_cau_san_xuat || (source.isPending ? "Đang tải…" : "Yêu cầu sản xuất")}</Link>],
      ["Ngày lập", dateTime(record.created_at)],
      [type === "xuat_linh_kien" ? "Mặt hàng đầu" : "Mã thành phẩm", firstItem ? `${firstItem.ten_mat_hang} — ${firstItem.ma_mat_hang || firstItem.sku}` : "—"],
      ["Số lượng xuất", record.chi_tiet.length === 1 ? `${number(firstLine.so_luong)} ${unitLabel(firstItem?.don_vi_tinh) || ""}` : `${record.chi_tiet.length} dòng mặt hàng`],
      ["Loại phiếu", issueTypeLabel(type)], ["Tổng tiền server chốt", money(record.tong_tien)],
      ...(record.ly_do_tu_choi ? [["Lý do từ chối", record.ly_do_tu_choi]] : []),
    ]} />
    <SavedLines lines={record.chi_tiet} items={items} prices />
    <QueryState query={source}>
      <ApprovalActions kind="issue" path={API.issues} snapshot={snapshot} items={items}
        assignedId={source.data?.data.nhan_vien_duoc_giao_id} />
    </QueryState>
  </div>;
}
