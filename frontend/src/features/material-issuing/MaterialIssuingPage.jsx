import { Link, Navigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useCollection, useDetail } from "../../lib/api/useResources.js";
import { money, dateTime } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { ApprovalActions } from "../../components/ApprovalActions.jsx";
import { SavedLines, statusFilter, dateFilters } from "../../components/ResourceFields.jsx";
import { dateRangeError } from "../../components/filterFields.js";
import { Notice, QueryState } from "../../components/QueryState.jsx";

const issueLabel = (value) => (value === "xuat_thanh_pham" ? "Thành phẩm" : "Linh kiện");

// UC-34–40: QLK reads/reviews source-generated issue documents, without editing their lines.
export function MaterialIssuingPage({ issueType }) {
  const { id } = useParams();
  const { user } = useAuth();
  const manager = user.ma_vai_tro === "quan_ly";
  const base = manager
    ? "/kho/phieu-xuat"
    : issueType === "xuat_thanh_pham"
      ? "/nv/xuat-tp"
      : "/nv/xuat-nvl";
  const collection = useCollection(API.issues, {
    sort: "-created_at",
    ...(issueType ? { loai_phieu: issueType } : {}),
  });
  const detail = useDetail(API.issues, id);
  const catalog = useCatalog();
  if (manager && id === "moi") return <Navigate to={base} replace />;
  return (
    <>
      <PageHeader
        title={
          manager
            ? "Phiếu xuất kho"
            : issueType === "xuat_thanh_pham"
              ? "Phiếu xuất thành phẩm"
              : "Phiếu xuất NVL / BTP"
        }
        subtitle={
          manager
            ? "Theo dõi, duyệt và từ chối phiếu xuất linh kiện, thành phẩm. Chỉ duyệt mới trừ tồn; nhân viên được giao lập phiếu từ yêu cầu."
            : "Chỉ xem phiếu liên quan đến công việc được giao."
        }
      />
      <Collection
        collection={collection}
        allowReset={manager}
        pageSizes={manager ? [20, 50, 100] : undefined}
        validate={manager ? dateRangeError : undefined}
        filters={[
          statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"]),
          ...(!issueType
            ? [
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
              ]
            : []),
          ...dateFilters,
        ]}
        columns={[
          {
            key: "ma_phieu_xuat",
            label: "Mã phiếu",
            render: (row) => <Link to={`${base}/${row.id}`}>{row.ma_phieu_xuat}</Link>,
          },
          { key: "loai_phieu", label: "Loại", render: (row) => issueLabel(row.loai_phieu) },
          ...(!manager
            ? [
                {
                  key: "source",
                  label: "Tham chiếu",
                  render: (row) =>
                    row.lenh_san_xuat_id
                      ? `LSX #${row.lenh_san_xuat_id}`
                      : `YCSX #${row.yeu_cau_san_xuat_id}`,
                },
              ]
            : []),
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
      <RecordPanel id={id} query={detail} base={base} title="Chi tiết phiếu xuất">
        {(snapshot) => (
          <QueryState query={catalog}>
            {snapshot ? (
              <IssueDetail
                snapshot={snapshot}
                items={catalog.data?.data || []}
                base={base}
                manager={manager}
              />
            ) : (
              <Notice>Bạn không có quyền lập phiếu xuất tại đây.</Notice>
            )}
          </QueryState>
        )}
      </RecordPanel>
    </>
  );
}

function IssueDetail({ snapshot, items, base, manager }) {
  const record = snapshot.data;
  const { user } = useAuth();
  const canReadCreator = manager || Number(record.nhan_vien_id) === Number(user.id);
  const creator = useDetail(API.employees, canReadCreator ? record.nhan_vien_id : undefined);
  const hasLegacyOrder = !manager && record.lenh_san_xuat_id;
  const source = useDetail(API.requests, hasLegacyOrder ? undefined : record.yeu_cau_san_xuat_id);
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
            canReadCreator ? (
              <QueryState query={creator}>{creator.data?.data.ho_ten || "Chưa có họ tên"}</QueryState>
            ) : (
              `Nhân viên #${record.nhan_vien_id}`
            ),
          ],
          ["Tạo lúc", dateTime(record.created_at)],
          ["Loại phiếu", issueLabel(record.loai_phieu)],
          [
            "Nguồn",
            hasLegacyOrder ? (
              `Lệnh #${record.lenh_san_xuat_id}`
            ) : (
              <QueryState query={source}>{source.data?.data.ma_yeu_cau_san_xuat}</QueryState>
            ),
          ],
          ["Tổng tiền đã chốt", money(record.tong_tien)],
          ["Lý do từ chối", record.ly_do_tu_choi],
        ]}
      />
      <SavedLines lines={record.chi_tiet} items={items} prices />
      <ApprovalActions
        kind="issue"
        path={API.issues}
        base={base}
        snapshot={snapshot}
        items={items}
        allowedActions={
          manager
            ? {
                approve: record.trang_thai === "cho_duyet",
                reject: record.trang_thai === "cho_duyet",
              }
            : undefined
        }
      />
    </div>
  );
}
