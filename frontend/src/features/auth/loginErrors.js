const LOGIN_ERROR_MESSAGES = {
  0: "Không kết nối được máy chủ. Vui lòng thử lại.",
  401: "Tên đăng nhập hoặc mật khẩu không đúng",
  422: "Vui lòng nhập đủ tên đăng nhập và mật khẩu",
  429: "Bạn thử quá nhiều lần. Vui lòng thử lại sau.",
};

// UC-01 Đăng nhập — A1–A4 (specs/use_cases/identity_access/UC-01.md)
export function loginErrorMessage(error) {
  if (error.status === 403) {
    return error.code === "tai_khoan_bi_vo_hieu_hoa"
      ? "Tài khoản đang bị khóa"
      : "Tài khoản không có quyền đăng nhập";
  }
  if (error.status >= 500 && error.status < 600) {
    return "Đăng nhập thất bại. Vui lòng thử lại.";
  }
  return LOGIN_ERROR_MESSAGES[error.status] || "Chưa thể đăng nhập. Vui lòng thử lại sau.";
}
