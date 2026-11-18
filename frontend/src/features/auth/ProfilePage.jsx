import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "./AuthProvider.jsx";
import { API } from "../../lib/api/endpoints.js";
import { writeResource } from "../../lib/api/client.js";
import { ROLE_LABELS } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { InfoGrid } from "../../components/RecordPanel.jsx";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { ErrorNotice } from "../../components/QueryState.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";

// UC-08 Đổi mật khẩu tài khoản — R3, A4: Hồ sơ chỉ hiển thị thông tin nhân viên; nhân viên tự đổi mật khẩu qua API riêng (specs/use_cases/identity_access/UC-08.md)
export function ProfilePage() {
  const { user } = useAuth();
  const isEmployee = user.ma_vai_tro === "nhan_vien";
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
        {isEmployee && <ChangePasswordCard />}
      </div>
    </>
  );
}

function ChangePasswordCard() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [error, setError] = useState(null);
  const [isPending, setIsPending] = useState(false);
  const { notify, confirm } = useFeedback();
  const { logout } = useAuth();

  function handleSubmit(event) {
    event.preventDefault();
    if (isPending) return;
    const errors = {};
    if (!currentPassword) {
      errors.currentPassword = "Vui lòng nhập mật khẩu hiện tại";
    }
    if (!newPassword || newPassword.length < 6) {
      errors.newPassword = "Mật khẩu mới phải có tối thiểu 6 ký tự";
    }
    if (newPassword !== confirmPassword) {
      errors.confirmPassword = "Mật khẩu nhập lại không khớp";
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});
    setError(null);

    confirm({
      title: "Xác nhận đổi mật khẩu",
      description: "Bạn có chắc chắn muốn đổi mật khẩu không?",
      impact: "Tất cả phiên đăng nhập hiện tại sẽ bị hủy và bạn sẽ cần đăng nhập lại.",
      label: "Xác nhận",
      variant: "profile-save",
      onConfirm: async () => {
        setIsPending(true);
        try {
          await writeResource({
            path: `${API.employees}/me/doi_mat_khau`,
            body: {
              mat_khau_hien_tai: currentPassword,
              mat_khau_moi: newPassword,
            },
            versioned: false,
          });
          notify("Đổi mật khẩu thành công. Vui lòng đăng nhập lại.");
          logout();
        } catch (failure) {
          setIsPending(false);
          if (failure?.code === "mat_khau_hien_tai_khong_dung" || failure?.status === 400) {
            setFieldErrors({ currentPassword: "Mật khẩu hiện tại không chính xác" });
          } else {
            setError(failure);
          }
        }
      },
    });
  }

  return (
    <Card title="Đổi mật khẩu">
      <form onSubmit={handleSubmit} className="stack">
        <ErrorNotice error={error} />
        <div style={{ position: "relative" }}>
          <Field
            label="Mật khẩu hiện tại"
            type={showCurrent ? "text" : "password"}
            required
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => {
              setCurrentPassword(e.target.value);
              if (fieldErrors.currentPassword) {
                setFieldErrors((prev) => ({ ...prev, currentPassword: null }));
              }
            }}
            placeholder="Nhập mật khẩu hiện tại"
            hint={fieldErrors.currentPassword}
            aria-invalid={fieldErrors.currentPassword ? true : undefined}
          />
          <button
            type="button"
            aria-label={showCurrent ? "Ẩn mật khẩu hiện tại" : "Hiện mật khẩu hiện tại"}
            aria-pressed={showCurrent}
            onClick={() => setShowCurrent(!showCurrent)}
            style={{
              position: "absolute",
              right: "12px",
              top: "34px",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "4px",
              color: "inherit",
              opacity: 0.7,
            }}
          >
            {showCurrent ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
          </button>
        </div>

        <div style={{ position: "relative" }}>
          <Field
            label="Mật khẩu mới"
            type={showNew ? "text" : "password"}
            required
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value);
              if (fieldErrors.newPassword) {
                setFieldErrors((prev) => ({ ...prev, newPassword: null }));
              }
            }}
            placeholder="Tối thiểu 6 ký tự"
            hint={fieldErrors.newPassword}
            aria-invalid={fieldErrors.newPassword ? true : undefined}
          />
          <button
            type="button"
            aria-label={showNew ? "Ẩn mật khẩu mới" : "Hiện mật khẩu mới"}
            aria-pressed={showNew}
            onClick={() => setShowNew(!showNew)}
            style={{
              position: "absolute",
              right: "12px",
              top: "34px",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "4px",
              color: "inherit",
              opacity: 0.7,
            }}
          >
            {showNew ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
          </button>
        </div>

        <div style={{ position: "relative" }}>
          <Field
            label="Nhập lại mật khẩu mới"
            type={showConfirm ? "text" : "password"}
            required
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              if (fieldErrors.confirmPassword) {
                setFieldErrors((prev) => ({ ...prev, confirmPassword: null }));
              }
            }}
            placeholder="Nhập lại mật khẩu mới"
            hint={fieldErrors.confirmPassword}
            aria-invalid={fieldErrors.confirmPassword ? true : undefined}
          />
          <button
            type="button"
            aria-label={showConfirm ? "Ẩn nhập lại mật khẩu mới" : "Hiện nhập lại mật khẩu mới"}
            aria-pressed={showConfirm}
            onClick={() => setShowConfirm(!showConfirm)}
            style={{
              position: "absolute",
              right: "12px",
              top: "34px",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "4px",
              color: "inherit",
              opacity: 0.7,
            }}
          >
            {showConfirm ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
          </button>
        </div>

        <div className="actions actions-end">
          <Button type="submit" disabled={isPending}>
            {isPending ? "Đang cập nhật…" : "Đổi mật khẩu"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
