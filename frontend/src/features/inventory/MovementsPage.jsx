import { PageHeader } from "../../components/PageHeader.jsx";
import { Collection } from "../../components/Collection.jsx";
import { QueryState } from "../../components/QueryState.jsx";
import { API } from "../../lib/api/endpoints.js";
import { useChoices, useCollection } from "../../lib/api/useResources.js";
import { dateTime, number } from "../../lib/format.js";
import { MOVEMENT_TYPES, SOURCE_LABELS, movementParams, signedQuantity } from "./stockMovements.js";
import { dateRangeError } from "../../components/filterFields.js";

// UC-42 Tra cứu lịch sử biến động kho — Main 2–4; R1–R3, A1, A2 (specs/use_cases/reporting/UC-42.md)
export function MovementsPage() {
  const collection = useCollection(API.stockMovements, {}, movementParams);
  const items = useChoices(API.items);
  const employees = useChoices(API.employees);
  return (
    <>
      <PageHeader
        title="Lịch sử biến động kho"
        subtitle="Mỗi lần tồn kho thay đổi do chứng từ đã ghi nhận vào kho. Khoảng thời gian tính theo giờ Việt Nam."
      />
      <QueryState query={items}>
        <QueryState query={employees}>
          <Collection
            title="Các lần biến động kho"
            collection={collection}
            allowReset
            pageSizes={[20, 50, 100]}
            search={false}
            validate={dateRangeError}
            filters={[
              {
                name: "mat_hang_id",
                label: "Mặt hàng",
                as: "select",
                options: [
                  { value: "", label: "Tất cả" },
                  ...(items.data ?? []).map((item) => ({
                    value: item.id,
                    label: `${item.ma_mat_hang} · ${item.ten_mat_hang}`,
                  })),
                ],
              },
              {
                name: "loai_giao_dich",
                label: "Loại nghiệp vụ",
                as: "select",
                options: [{ value: "", label: "Tất cả" }, ...MOVEMENT_TYPES],
              },
              {
                name: "nhan_vien_id",
                label: "Nhân viên",
                as: "select",
                options: [
                  { value: "", label: "Tất cả" },
                  ...(employees.data ?? []).map((employee) => ({
                    value: employee.id,
                    label: `${employee.ma_nhan_vien} · ${employee.ho_ten ?? "—"}`,
                  })),
                ],
              },
              { name: "tu_ngay", label: "Từ ngày", type: "date" },
              { name: "den_ngay", label: "Đến ngày", type: "date" },
            ]}
            columns={[
              { key: "posted_at", label: "Thời điểm", render: (row) => dateTime(row.posted_at) },
              {
                key: "mat_hang",
                label: "Mặt hàng",
                render: (row) => `${row.mat_hang.ma_mat_hang} · ${row.mat_hang.ten_mat_hang}`,
              },
              {
                key: "loai_giao_dich",
                label: "Loại nghiệp vụ",
                render: (row) =>
                  MOVEMENT_TYPES.find((type) => type.value === row.loai_giao_dich)?.label,
              },
              {
                key: "so_luong_bien_dong",
                label: "Số lượng thay đổi",
                numeric: true,
                render: (row) => signedQuantity(row.so_luong_bien_dong),
              },
              {
                key: "so_luong_ton_sau",
                label: "Tồn sau",
                numeric: true,
                render: (row) => number(row.so_luong_ton_sau),
              },
              {
                key: "chung_tu",
                label: "Chứng từ gốc",
                render: (row) => (
                  <>
                    {row.chung_tu.ma}
                    <small>{SOURCE_LABELS[row.chung_tu.loai]}</small>
                  </>
                ),
              },
              {
                key: "nhan_vien",
                label: "Nhân viên",
                render: (row) => `${row.nhan_vien.ma_nhan_vien} · ${row.nhan_vien.ho_ten ?? "—"}`,
              },
            ]}
          />
        </QueryState>
      </QueryState>
    </>
  );
}
