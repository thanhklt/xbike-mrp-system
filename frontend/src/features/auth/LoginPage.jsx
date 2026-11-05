import { useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Phone } from "lucide-react";
import { useAuth } from "./AuthProvider.jsx";
import { homeFor } from "./permissions.js";
import { Button } from "../../components/Button.jsx";
import { Field } from "../../components/Field.jsx";
import { ErrorNotice } from "../../components/QueryState.jsx";
import { LoginCarousel } from "./LoginCarousel.jsx";
import { LOGIN_SLIDES, LOGIN_SLIDE_INTERVAL_MS } from "./loginSlides.js";

const SUPPORT_PHONE = { display: "0900 000 000", tel: "0900000000" };

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
      <main className="login-main">
        <div className="login-card">
          <LoginCarousel slides={LOGIN_SLIDES} interval={LOGIN_SLIDE_INTERVAL_MS} />
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
              <div className="password-field">
                <Field
                  label="Mật khẩu"
                  type={visible ? "text" : "password"}
                  autoComplete="current-password"
                  maxLength={1024}
                  required
                  placeholder="Nhập mật khẩu"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  className="password-toggle"
                  aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  aria-pressed={visible}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? (
                    <EyeOff aria-hidden="true" size={30} strokeWidth={1.75} />
                  ) : (
                    <Eye aria-hidden="true" size={30} strokeWidth={1.75} />
                  )}
                </button>
              </div>
              <Button type="submit" disabled={busy}>
                {busy ? "Đang đăng nhập…" : "Đăng nhập"}
                {!busy && <ArrowRight aria-hidden="true" size={26} strokeWidth={2.25} />}
              </Button>
            </form>
            <div className="login-support">
              <Phone aria-hidden="true" size={40} strokeWidth={1.5} />
              <div>
                <strong>Hỗ trợ Admin</strong>
                <a href={`tel:${SUPPORT_PHONE.tel}`}>{SUPPORT_PHONE.display}</a>
              </div>
            </div>
          </section>
        </div>
      </main>
      <footer className="login-footer">© {new Date().getFullYear()} XBIKE · Hệ thống nội bộ</footer>
    </div>
  );
}
