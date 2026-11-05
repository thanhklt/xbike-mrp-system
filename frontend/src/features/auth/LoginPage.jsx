import { useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthProvider.jsx";
import { homeFor } from "./permissions.js";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { ErrorNotice } from "../../components/QueryState.jsx";
export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const pending = useRef(false);
  if (user) return <Navigate to={homeFor(user.ma_vai_tro)} replace />;
  async function submit(event) {
    event.preventDefault();
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError(null);
    try {
      const employee = await login({ ten_dang_nhap: username.trim(), mat_khau: password });
      setPassword("");
      navigate(homeFor(employee.ma_vai_tro), { replace: true });
    } catch (failure) {
      setError(failure);
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="login-page">
      <header className="login-header">
        <div className="brand">
          XBIKE<small>Hệ thống quản lý kho & sản xuất</small>
        </div>
      </header>
      <main className="login-main">
        <div className="login-card">
          <section className="login-intro">
            <div className="brand">
              XBIKE<small>MRP · Kho · Sản xuất</small>
            </div>
            <h2>
              Kiểm soát kho.
              <br />
              Điều phối sản xuất.
            </h2>
            <p>
              Quản lý nguyên vật liệu, BOM, phiếu nhập – xuất và chứng từ hoàn thành sản xuất trên
              một hệ thống.
            </p>
            <hr />
            <span>Dành cho quản trị viên, quản lý kho và nhân viên</span>
          </section>
          <section className="login-form">
            <form className="stack" onSubmit={submit}>
              <h1>Đăng nhập</h1>
              <p className="muted">Sử dụng tài khoản được quản trị viên cấp.</p>
              <ErrorNotice error={error} />
              <Field
                label="Tên đăng nhập"
                autoComplete="username"
                maxLength={255}
                required
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Nhập tên đăng nhập"
              />
              <div>
                <Field
                  label="Mật khẩu"
                  type={visible ? "text" : "password"}
                  autoComplete="current-password"
                  maxLength={1024}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="text-button password-toggle"
                  aria-pressed={visible}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                </button>
              </div>
              <Button type="submit" disabled={busy}>
                {busy ? "Đang đăng nhập…" : "Đăng nhập"}
              </Button>
              <small className="muted">
                Gặp sự cố đăng nhập? Liên hệ quản trị viên để được hỗ trợ.
              </small>
            </form>
          </section>
        </div>
      </main>
      <footer className="login-footer">© {new Date().getFullYear()} XBIKE · Hệ thống nội bộ</footer>
    </div>
  );
}
