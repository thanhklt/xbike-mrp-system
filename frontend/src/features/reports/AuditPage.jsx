import { useMemo } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { auditParams } from "../../lib/api/contract.js";
import { useChoices, useCollection, useDetail } from "../../lib/api/useResources.js";
import { dateTime, unitLabel } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { Notice } from "../../components/QueryState.jsx";
import { Button } from "../../components/Button.jsx";
import { dateRangeError } from "../../components/filterFields.js";
import { RecordPanel, InfoGrid } from "../../components/RecordPanel.jsx";
import { Badge } from "../../components/Badge.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { auditActionLabel, auditObjectLabel } from "../dashboard/auditFormat.js";
import {
  adminAuditFilters,
  auditFilters,
  auditActorLookup,
  auditDetailEntries,
  auditShortageRows,
} from "./auditHistory.js";

// UC-43 Xem lịch sử thao tác — Main 1–4; R5, A1: tra cứu danh sách (specs/use_cases/audit/UC-43.md)
export function AuditPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user.ma_vai_tro === "quan_tri_vien";
  const base = isAdmin ? "/admin/lich-su" : "/kho/lich-su";
  const collection = useCollection(API.audit, { sort: "-created_at" }, auditParams);
  const detail = useDetail(API.audit, id);
  const employees = useChoices(API.employees);
  const employeeRows = useMemo(() => employees.data || [], [employees.data]);
  const actorLabel = useMemo(() => auditActorLookup(employeeRows), [employeeRows]);
  const filters = useMemo(
    () => (isAdmin ? adminAuditFilters() : auditFilters(employeeRows)),
    [isAdmin, employeeRows],
  );
  // Màn chỉ đọc: không có chế độ tạo mới, "/moi" quay về danh sách.
  if (id === "moi") return <Navigate to={base} replace />;
  return (
    <>
      <PageHeader variant="large" title="Lịch sử thao tác" />
      {/* Cùng bố cục với QueryState khi lỗi: thông báo và nút "Tải lại" gọi refetch, chỉ đọc. */}
      {employees.isError && (
        <div className="stack">
          <Notice tone="warning">
            {isAdmin
              ? "Không thể tải danh sách nhân viên. Người thực hiện hiển thị theo ID."
              : "Không thể tải danh sách nhân viên. Bộ lọc Người thực hiện tạm chỉ có Tất cả và người thực hiện hiển thị theo ID."}
          </Notice>
          <Button
            variant="secondary"
            onClick={() => employees.refetch()}
            disabled={employees.isFetching}
          >
            Tải lại
          </Button>
        </div>
      )}
      {/* Tắt ô tìm kiếm: backend chỉ tìm mã thô trong loại đối tượng/thao tác/lý do, đã có bộ lọc chuyên biệt. */}
      <Collection
        collection={collection}
        search={false}
        validate={dateRangeError}
        filters={filters}
        columns={[
          { key: "created_at", label: "Thời gian", render: (row) => dateTime(row.created_at) },
          {
            key: "nhan_vien_id",
            label: "Người thực hiện",
            render: (row) => actorLabel(row.nhan_vien_id),
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
        {(snapshot) => snapshot && <AuditDetail record={snapshot.data} actorLabel={actorLabel} />}
      </RecordPanel>
    </>
  );
}

// UC-43 Xem lịch sử thao tác — Main 5–6; R2, R3, R4, R6: xem chi tiết (specs/use_cases/audit/UC-43.md)
function AuditDetail({ record, actorLabel }) {
  const entries = auditDetailEntries(record, actorLabel).map(([label, value, kind]) => [
    label,
    kind === "status" && value !== null && value !== undefined ? <Badge status={value} /> : value,
  ]);
  const shortage = auditShortageRows(record);
  return (
    <div className="stack">
      <InfoGrid entries={entries} />
      {shortage && (
        <div>
          <h3>Danh sách thiếu tại thời điểm thao tác</h3>
          <DataTable
            rows={shortage}
            columns={[
              {
                key: "mat_hang_id",
                label: "Mặt hàng",
                render: (row) =>
                  [row.ma_mat_hang, row.ten_mat_hang].filter(Boolean).join(" · ") ||
                  `#${row.mat_hang_id}`,
              },
              { key: "don_vi_tinh", label: "Đơn vị", render: (row) => unitLabel(row.don_vi_tinh) },
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
