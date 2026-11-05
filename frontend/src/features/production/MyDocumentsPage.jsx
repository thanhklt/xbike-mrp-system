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
  const [kind, setKind] = useState("completion");
  return (
    <>
      <PageHeader
        title="Phiếu của tôi"
        subtitle="Chứng từ hoàn thành do bạn lập và phiếu xuất liên quan đến công việc được giao."
      />
      <div className="tabs" aria-label="Loại chứng từ">
        {[
          ["completion", "Hoàn thành SX của tôi"],
          ["xuat_vat_tu", "Phiếu xuất NVL / BTP liên quan"],
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
  const completion = kind === "completion";
  const collection = useCollection(completion ? API.completions : API.issues, {
    sort: "-id",
    ...(!completion ? { loai_phieu: kind } : {}),
  });
  const base = completion
    ? "/nv/hoan-thanh"
    : kind === "xuat_vat_tu"
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
            <Link to={`${base}/${row.id}`}>{row.ma_phieu || row.ma_phieu_xuat}</Link>
          ),
        },
        {
          key: "source",
          label: "Tham chiếu",
          render: (row) =>
            row.lenh_san_xuat_id
              ? `Lệnh #${row.lenh_san_xuat_id}`
              : `Yêu cầu #${row.yeu_cau_san_xuat_id}`,
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
              {completion && row.trang_thai === "nhap" ? "Mở nháp" : "Xem"} →
            </Link>
          ),
        },
      ]}
    />
  );
}
