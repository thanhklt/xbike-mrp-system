import { Link } from "react-router-dom";
import { API } from "../../lib/api/endpoints.js";
import { useCatalog, useChoices, useCollection } from "../../lib/api/useResources.js";
import { dateTime, employeeName, itemName } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { Badge } from "../../components/Badge.jsx";
import { statusFilter } from "../../components/ResourceFields.jsx";
import { dateRangeError } from "../../components/filterFields.js";
import { completionListFilters } from "./completionForm.js";
import { REQUEST_TYPE_LABELS } from "./requestForm.js";

// UC-33 Xem danh sách chứng từ hoàn thành sản xuất — Main 1–5; A1 danh sách, lọc và mở yêu cầu (specs/use_cases/production/UC-33.md)
export function CompletionListPage() {
  const collection = useCollection(API.completions);
  const catalog = useCatalog();
  const employees = useChoices(API.employees);
  const items = catalog.data?.data || [];
  const status = statusFilter(["cho_duyet", "da_duyet", "tu_choi"]);
  return (
    <>
      <PageHeader
        title="Chứng từ hoàn thành sản xuất"
        subtitle="Chứng từ nhân viên đã gửi; mở để duyệt hoặc từ chối."
      />
      <Collection
        collection={collection}
        allowReset
        pageSizes={[20, 50, 100]}
        search={false}
        validate={dateRangeError}
        filters={[
          status,
          ...completionListFilters(items, employees.data || []),
        ]}
        columns={[
          {
            key: "ma_phieu", label: "Mã chứng từ",
            render: (row) => <Link to={`/kho/yeu-cau/${row.yeu_cau_san_xuat_id}`}>{row.ma_phieu}</Link>,
          },
          { key: "ma_yeu_cau_san_xuat", label: "Mã yêu cầu" },
          { key: "mat_hang_id", label: "Thành phẩm", render: (row) => itemName(items, row.mat_hang_id) },
          { key: "loai_yeu_cau", label: "Loại yêu cầu", render: (row) => REQUEST_TYPE_LABELS[row.loai_yeu_cau] },
          { key: "nhan_vien_id", label: "Nhân viên", render: (row) => employeeName(employees.data || [], row.nhan_vien_id) },
          { key: "so_luong_hoan_thanh", label: "Số lượng hoàn thành", numeric: true },
          { key: "finish_time", label: "Thời điểm hoàn thành", render: (row) => dateTime(row.finish_time) },
          { key: "trang_thai", label: "Trạng thái", render: (row) => <Badge status={row.trang_thai} /> },
          {
            key: "actions", label: "Thao tác",
            render: (row) => <Link to={`/kho/yeu-cau/${row.yeu_cau_san_xuat_id}`}>Mở →</Link>,
          },
        ]}
      />
    </>
  );
}
