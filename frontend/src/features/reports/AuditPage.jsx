import { Link, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { auditParams } from "../../lib/api/contract.js";
import { useChoices, useCollection, useDetail } from "../../lib/api/useResources.js";
import { dateTime } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { auditActionLabel, auditObjectLabel } from "../dashboard/auditFormat.js";
import {
  auditFilters,
  auditActorLabel,
  auditDetailEntries,
  auditShortageRows,
} from "./auditHistory.js";

// UC-43 Xem lịch sử thao tác — Main 1–4; R5, A1: tra cứu danh sách (specs/use_cases/audit/UC-43.md)
export function AuditPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const base = user.ma_vai_tro === "quan_tri_vien" ? "/admin/lich-su" : "/kho/lich-su";
  const collection = useCollection(API.audit, { sort: "-created_at" }, auditParams);
  const detail = useDetail(API.audit, id);
  const employees = useChoices(API.employees);
  const employeeRows = employees.data || [];
  return (
    <>
      <PageHeader
        title="Lịch sử thao tác"
        subtitle="Tra cứu người thực hiện, thời điểm và dữ liệu trước/sau của các thao tác đã lưu."
      />
      <Collection
        collection={collection}
        filters={auditFilters(employeeRows)}
        columns={[
          { key: "created_at", label: "Thời gian", render: (row) => dateTime(row.created_at) },
          {
            key: "nhan_vien_id",
            label: "Người thực hiện",
            render: (row) => auditActorLabel(employeeRows, row.nhan_vien_id),
          },
          {
            key: "loai_doi_tuong",
            label: "Đối tượng",
            render: (row) => (
              <>
                {auditObjectLabel(row.loai_doi_tuong)}
                <small>#{row.doi_tuong_id}</small>
              </>
            ),
          },
          {
            key: "thao_tac",
            label: "Thao tác",
            render: (row) => auditActionLabel(row.thao_tac),
          },
          { key: "ly_do", label: "Lý do" },
          {
            key: "action",
            label: "Chi tiết",
            render: (row) => <Link to={`${base}/${row.id}`}>Mở →</Link>,
          },
        ]}
      />
      <RecordPanel id={id} query={detail} base={base} title="Chi tiết lịch sử thao tác">
        {(snapshot) => snapshot && <AuditDetail record={snapshot.data} employees={employeeRows} />}
      </RecordPanel>
    </>
  );
}

// UC-43 Xem lịch sử thao tác — Main 5–6; R2, R3, R4, R6: xem chi tiết (specs/use_cases/audit/UC-43.md)
function AuditDetail({ record, employees }) {
  const entries = auditDetailEntries(record, employees).map(([label, value]) => [
    label,
    ["Trạng thái trước", "Trạng thái sau"].includes(label) &&
    value !== null &&
    value !== undefined ? (
      <Badge status={value} />
    ) : (
      value
    ),
  ]);
  return (
    <div className="stack">
      <InfoGrid entries={entries} />
      {Array.isArray(record.du_lieu_sau?.danh_sach_thieu) && (
        <div>
          <h3>Danh sách thiếu tại thời điểm thao tác</h3>
          <DataTable
            rows={auditShortageRows(record).map((row, index) => ({ ...row, id: index }))}
            columns={[
              {
                key: "mat_hang_id",
                label: "Mặt hàng",
                render: (row) =>
                  [row.ma_mat_hang, row.ten_mat_hang].filter(Boolean).join(" · ") ||
                  `#${row.mat_hang_id}`,
              },
              { key: "don_vi_tinh", label: "Đơn vị" },
              { key: "so_luong_can", label: "Cần", numeric: true },
              { key: "so_luong_con_dung", label: "Còn dùng", numeric: true },
              { key: "so_luong_thieu", label: "Thiếu", numeric: true },
            ]}
          />
        </div>
      )}
      {[
        ["Dữ liệu trước", record.du_lieu_truoc],
        ["Dữ liệu sau", record.du_lieu_sau],
      ].map(([label, value]) => (
        <div key={label}>
          <h3>{label}</h3>
          {value === null || value === undefined ? (
            <p className="empty-state">Không có dữ liệu</p>
          ) : (
            <pre className="audit-json">{JSON.stringify(value, null, 2)}</pre>
          )}
        </div>
      ))}
    </div>
  );
}
