import { useState } from "react";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { Field } from "../../components/Field.jsx";
import { Button } from "../../components/Button.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { Notice } from "../../components/QueryState.jsx";
import { itemTypeOptions } from "../../components/ResourceFields.jsx";
export function ReportsPage() {
  const [period, setPeriod] = useState("thang");
  return (
    <>
      <PageHeader
        title="Thống kê nhập – xuất – tồn"
        subtitle="Số liệu báo cáo chỉ tính giao dịch đã ghi sổ, bao gồm điều chỉnh có dấu đúng một lần."
      />
      <Notice tone="warning">
        Báo cáo chưa có API được triển khai. Chưa thể truy xuất số liệu tháng/quý/năm; giao diện
        không hiển thị số liệu giả hoặc tính từ danh sách phân trang.
      </Notice>
      <Card title="Kỳ thống kê">
        <div className="filters">
          <Field
            as="select"
            label="Kỳ thống kê"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
          >
            <option value="thang">Tháng</option>
            <option value="quy">Quý</option>
            <option value="nam">Năm</option>
          </Field>
          <Field
            label="Năm"
            type="number"
            defaultValue={new Date().getFullYear()}
            min="1"
            max="9999"
          />
          {period === "thang" && (
            <Field label="Tháng" type="number" min="1" max="12" defaultValue="1" />
          )}
          {period === "quy" && (
            <Field label="Quý" as="select">
              <option>1</option>
              <option>2</option>
              <option>3</option>
              <option>4</option>
            </Field>
          )}
          <Field label="Loại mặt hàng" as="select" options={itemTypeOptions} />
          <Button reason="Chờ API báo cáo nhập–xuất–tồn.">Xem thống kê</Button>
        </div>
      </Card>
      <Card title="Nhập – xuất – tồn theo mặt hàng">
        <DataTable
          empty="Chưa có số liệu báo cáo — đang chờ API."
          columns={[
            { key: "ten_mat_hang", label: "Mặt hàng" },
            { key: "ton_dau_ky", label: "Tồn đầu kỳ", numeric: true },
            { key: "nhap_trong_ky", label: "Nhập", numeric: true },
            { key: "xuat_trong_ky", label: "Xuất", numeric: true },
            { key: "dieu_chinh_trong_ky", label: "Điều chỉnh", numeric: true },
            { key: "ton_cuoi_ky", label: "Tồn cuối kỳ", numeric: true },
          ]}
        />
      </Card>
    </>
  );
}
