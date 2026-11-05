import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { Notice } from "../../components/QueryState.jsx";
export function MovementsPage() {
  return (
    <>
      <PageHeader
        title="Giao dịch kho"
        subtitle="Sổ biến động nhập, xuất, hoàn thành sản xuất và điều chỉnh."
      />
      <Notice tone="warning">
        Phần đọc giao dịch kho chưa đồng bộ với schema hiện tại. Chức năng tra cứu đang chờ backend;
        tồn hiện tại vẫn xem được tại Mặt hàng và tồn kho.
      </Notice>
      <Card>
        <div className="filters">
          <Field label="Mặt hàng" disabled placeholder="Mã hoặc tên mặt hàng" />
          <Field label="Từ ngày" type="date" disabled />
          <Field label="Đến ngày" type="date" disabled />
          <Button reason="Chờ API đọc sổ kho được đồng bộ.">Lọc giao dịch</Button>
        </div>
        <DataTable
          empty="Chưa thể tải sổ giao dịch kho."
          columns={[
            { key: "posted_at", label: "Thời gian" },
            { key: "mat_hang_id", label: "Mặt hàng" },
            { key: "loai_giao_dich", label: "Loại giao dịch" },
            { key: "source", label: "Chứng từ nguồn" },
            { key: "so_luong_bien_dong", label: "Biến động", numeric: true },
            { key: "nhan_vien_id", label: "Người thực hiện" },
          ]}
        />
      </Card>
    </>
  );
}
