import { Link } from "react-router-dom";
import { useChoices } from "../../lib/api/useResources.js";
import { API } from "../../lib/api/endpoints.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { Button } from "../../components/Button.jsx";
import { DataTable } from "../../components/DataTable.jsx";
import { QueryState, Notice } from "../../components/QueryState.jsx";
const scope = {
  quan_tri_vien: "Tài khoản, vai trò và lịch sử rút gọn",
  quan_ly: "Danh mục, kho, sản xuất, duyệt và điều chỉnh",
  nhan_vien: "Công việc được giao và chứng từ hoàn thành của mình",
};
export function RolesPage() {
  const roles = useChoices(API.roles);
  return (
    <>
      <PageHeader
        title="Vai trò"
        subtitle="Mỗi tài khoản có đúng một vai trò; backend kiểm tra quyền ở mỗi request."
      />
      <Notice>
        Mã vai trò và phạm vi theo API đã chốt. Không có chức năng tự tạo hoặc sửa vai trò.
      </Notice>
      <Card>
        <QueryState query={roles}>
          <DataTable
            rows={roles.data}
            columns={[
              { key: "ma_vai_tro", label: "Mã vai trò" },
              { key: "ten_vai_tro", label: "Tên hiển thị" },
              { key: "scope", label: "Phạm vi", render: (row) => scope[row.ma_vai_tro] },
              {
                key: "action",
                label: "Thao tác",
                render: () => (
                  <div className="actions">
                    <Link to="/admin/tai-khoan">Xem tài khoản</Link>
                    <Button variant="secondary" reason="Chưa có API sửa tên vai trò.">
                      Sửa tên
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        </QueryState>
      </Card>
    </>
  );
}
