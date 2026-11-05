import { API } from "../../lib/api/endpoints.js";
import { auditParams } from "../../lib/api/contract.js";
import { useCollection } from "../../lib/api/useResources.js";
import { dateTime } from "../../lib/format.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { Notice } from "../../components/QueryState.jsx";
export function AuditPage() {
  const { user } = useAuth();
  const collection = useCollection(API.audit, { sort: "-created_at" }, auditParams);
  const manager = user.ma_vai_tro === "quan_ly";
  return (
    <>
      <PageHeader
        title="Lịch sử thao tác"
        subtitle={
          manager
            ? "Tra cứu các thao tác nghiệp vụ được lưu bởi backend."
            : "Lịch sử rút gọn. Quản trị viên không được xem snapshot dữ liệu nghiệp vụ."
        }
      />
      <Notice>
        Hiện hỗ trợ tìm kiếm và sắp xếp theo khả năng API lịch sử hiện hành. Bộ lọc chuyên sâu theo
        ngày, nhân viên và đối tượng chưa được hỗ trợ.
      </Notice>
      <Collection
        collection={collection}
        filters={[
          {
            name: "sort",
            label: "Sắp xếp",
            as: "select",
            options: [
              { value: "-created_at", label: "Mới nhất" },
              { value: "created_at", label: "Cũ nhất" },
              { value: "-id", label: "ID giảm dần" },
            ],
          },
        ]}
        columns={[
          { key: "created_at", label: "Thời gian", render: (row) => dateTime(row.created_at) },
          { key: "nhan_vien_id", label: "Nhân viên", render: (row) => `#${row.nhan_vien_id}` },
          {
            key: "loai_doi_tuong",
            label: "Đối tượng",
            render: (row) => (
              <>
                {row.loai_doi_tuong}
                <small>#{row.doi_tuong_id}</small>
              </>
            ),
          },
          { key: "thao_tac", label: "Thao tác" },
          { key: "ly_do", label: "Lý do" },
          ...(manager
            ? [
                {
                  key: "snapshot",
                  label: "Dữ liệu",
                  render: (row) => (
                    <details>
                      <summary>Trước / sau</summary>
                      <pre className="audit-json">
                        {JSON.stringify(
                          { truoc: row.du_lieu_truoc, sau: row.du_lieu_sau },
                          null,
                          2,
                        )}
                      </pre>
                    </details>
                  ),
                },
              ]
            : []),
        ]}
      />
    </>
  );
}
