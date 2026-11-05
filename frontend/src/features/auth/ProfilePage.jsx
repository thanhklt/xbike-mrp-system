import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./AuthProvider.jsx";
import { API } from "../../lib/api/endpoints.js";
import { useWrite } from "../../lib/api/useResources.js";
import { ROLE_LABELS } from "../../lib/format.js";
import { PageHeader } from "../../components/PageHeader.jsx";
import { Card } from "../../components/Card.jsx";
import { Field } from "../../components/Field.jsx";
import { InfoGrid } from "../../components/RecordPanel.jsx";
import { Button } from "../../components/Button.jsx";
import { useFeedback } from "../../components/FeedbackProvider.jsx";
export function ProfilePage() {
  const { user, logout } = useAuth();
  const { confirm } = useFeedback();
  const navigate = useNavigate();
  const mutation = useWrite();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  function submit(event) {
    event.preventDefault();
    confirm({
      title: "Đổi mật khẩu",
      description: "Mật khẩu mới sẽ vô hiệu hóa mọi phiên đăng nhập cũ, bao gồm phiên hiện tại.",
      label: "Đổi mật khẩu",
      onConfirm: async () => {
        await mutation.mutateAsync({
          path: API.password,
          body: { mat_khau_hien_tai: current, mat_khau_moi: next },
          versioned: false,
        });
        setCurrent("");
        setNext("");
        setRepeat("");
        logout("Đã đổi mật khẩu. Vui lòng đăng nhập lại.");
        navigate("/dang-nhap", { replace: true });
      },
    });
  }
  return (
    <>
      <PageHeader title="Hồ sơ & đổi mật khẩu" subtitle="Thông tin tài khoản đang sử dụng." />
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
        <Card title="Đổi mật khẩu">
          <form className="stack" onSubmit={submit}>
            <Field
              label="Mật khẩu hiện tại"
              type="password"
              required
              maxLength={1024}
              autoComplete="current-password"
              value={current}
              onChange={(event) => setCurrent(event.target.value)}
            />
            <Field
              label="Mật khẩu mới"
              type="password"
              required
              minLength={8}
              maxLength={1024}
              autoComplete="new-password"
              value={next}
              onChange={(event) => setNext(event.target.value)}
            />
            <Field
              label="Nhập lại mật khẩu mới"
              type="password"
              required
              autoComplete="new-password"
              value={repeat}
              onChange={(event) => setRepeat(event.target.value)}
              hint={
                repeat && repeat !== next
                  ? "Mật khẩu nhập lại chưa khớp."
                  : "Mật khẩu mới từ 8 ký tự. Sau khi đổi phải đăng nhập lại."
              }
            />
            <Button type="submit" disabled={!next || next !== repeat}>
              Đổi mật khẩu
            </Button>
          </form>
        </Card>
      </div>
    </>
  );
}
