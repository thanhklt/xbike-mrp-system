import { useState } from "react";
import { Link } from "react-router-dom";
import { useCollection } from "../../lib/api/useResources.js";
import { API } from "../../lib/api/endpoints.js";
import { dateTime } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { Badge } from "../../components/Badge.jsx";
import { statusFilter } from "../../components/ResourceFields.jsx";
export function MyDocumentsPage() {
  const [kind, setKind] = useState("xuat_linh_kien");
  return (
    <>
      <PageHeader
        title="Phiếu của tôi"
        subtitle="Phiếu xuất liên quan đến yêu cầu sản xuất được giao."
      />
      <div className="tabs" aria-label="Loại chứng từ">
        {[
          ["xuat_linh_kien", "Phiếu xuất linh kiện liên quan"],
          ["xuat_thanh_pham", "Phiếu xuất thành phẩm liên quan"],
        ].map(([key, label]) => (
          <button type="button" key={key} aria-pressed={kind === key} onClick={() => setKind(key)}>
            {label}
          </button>
        ))}
      </div>
      <DocumentList key={kind} kind={kind} />
    </>
  );
}
function DocumentList({ kind }) {
  const collection = useCollection(API.issues, {
    sort: "-id",
    loai_phieu: kind,
  });
  const base = kind === "xuat_linh_kien"
    ? "/nv/xuat-nvl"
    : "/nv/xuat-tp";
  return (
    <Collection
      collection={collection}
      filters={[statusFilter(["nhap", "cho_duyet", "da_duyet", "tu_choi"])]}
      columns={[
        {
          key: "code",
          label: "Mã chứng từ",
          render: (row) => (
            <Link to={`${base}/${row.id}`}>{row.ma_phieu_xuat}</Link>
          ),
        },
        {
          key: "source",
          label: "Tham chiếu",
          render: (row) =>
            `Yêu cầu #${row.yeu_cau_san_xuat_id}`,
        },
        { key: "created_at", label: "Tạo lúc", render: (row) => dateTime(row.created_at) },
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
              Xem →
            </Link>
          ),
        },
      ]}
    />
  );
}
