import { useAuth } from "./AuthProvider.jsx";
import { ROLE_LABELS } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { InfoGrid } from "../../components/RecordPanel.jsx";

// UC-08 Đổi mật khẩu tài khoản — R3, A4: Hồ sơ chỉ hiển thị thông tin nhân viên (specs/use_cases/identity_access/UC-08.md)
export function ProfilePage() {
  const { user } = useAuth();
  return (
    <>
      <PageHeader title="Hồ sơ" subtitle="Thông tin tài khoản đang sử dụng." />
      <div className="dashboard-columns">
        <Card title="Hồ sơ nhân viên">
          <InfoGrid
            entries={[
              ["Mã nhân viên", user.ma_nhan_vien],
              ["Họ tên", user.ho_ten],
              ["Tên đăng nhập", user.ten_dang_nhap],
              ["Vai trò", ROLE_LABELS[user.ma_vai_tro]],
              ["Email", user.email],
              ["Số điện thoại", user.so_dien_thoai],
              ["Ngày sinh", user.ngay_sinh],
              ["Ngày vào làm", user.ngay_vao_lam],
            ]}
          />
        </Card>
      </div>
    </>
  );
}
