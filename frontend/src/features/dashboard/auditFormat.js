import { ROLE_LABELS } from "../../lib/format.js";

const ACTION_LABELS = {
  tao: "Tạo",
  sua: "Cập nhật",
  xoa_nhap: "Xóa nháp",
  gui: "Gửi",
  bat_dau: "Bắt đầu",
  duyet: "Duyệt",
  tu_choi: "Từ chối",
  ve_nhap: "Chuyển về nháp",
  hoan_tat: "Hoàn tất",
  cap_quyen: "Cấp quyền",
  thu_hoi_quyen: "Thu hồi quyền",
  vo_hieu_hoa: "Vô hiệu hóa",
  huy: "Hủy",
  ghi_nhan_loi: "Ghi nhận lỗi",
  nhan_xu_ly: "Nhận xử lý",
  giai_quyet: "Giải quyết",
  xac_nhan: "Xác nhận",
};

const OBJECT_LABELS = {
  nhan_vien: "tài khoản",
  vai_tro: "vai trò",
  mat_hang: "mặt hàng",
  nha_cung_cap: "nhà cung cấp",
  cong_thuc: "BOM",
  phieu_nhap: "phiếu nhập",
  phieu_xuat: "phiếu xuất",
  yeu_cau_san_xuat: "yêu cầu sản xuất",
  lenh_san_xuat: "lệnh sản xuất",
  chung_tu_hoan_thanh_san_xuat: "chứng từ hoàn thành SX",
  phieu_dieu_chinh_kho: "phiếu điều chỉnh kho",
  ticket_loi_dieu_chinh: "ticket lỗi điều chỉnh",
};

const CODE_FIELDS = {
  mat_hang: "ma_mat_hang",
  nha_cung_cap: "ma_ncc",
  phieu_nhap: "ma_phieu_nhap",
  phieu_xuat: "ma_phieu_xuat",
  yeu_cau_san_xuat: "ma_yeu_cau_san_xuat",
  lenh_san_xuat: "ma_lenh_san_xuat",
  chung_tu_hoan_thanh_san_xuat: "ma_phieu",
  phieu_dieu_chinh_kho: "ma_phieu",
  ticket_loi_dieu_chinh: "ma_ticket",
};

const PROFILE_FIELDS = [
  ["ho_ten", "họ tên"],
  ["ngay_sinh", "ngày sinh"],
  ["so_dien_thoai", "số điện thoại"],
  ["email", "email"],
  ["ngay_vao_lam", "ngày vào làm"],
  ["he_so_luong", "hệ số lương"],
];

export function formatAuditAction(entry) {
  if (entry.loai_doi_tuong === "nhan_vien") {
    if (entry.thao_tac === "dang_nhap") return "Đăng nhập";
    if (entry.thao_tac === "cap_quyen") return "Phân quyền";
    if (entry.thao_tac === "thu_hoi_quyen") return "Thu hồi quyền";
    if (entry.thao_tac === "sua") {
      if (entry.du_lieu_sau?.da_doi_mat_khau === true) return "Đổi mật khẩu";
      if (entry.du_lieu_sau?.da_dat_lai_mat_khau === true) return "Đặt lại mật khẩu";
      if (
        entry.du_lieu_truoc?.trang_thai === "bi_khoa" &&
        entry.du_lieu_sau?.trang_thai === "hoat_dong"
      )
        return "Mở khóa tài khoản";
    }
  }
  const verb = ACTION_LABELS[entry.thao_tac] || entry.thao_tac;
  const noun = OBJECT_LABELS[entry.loai_doi_tuong] || entry.loai_doi_tuong;
  return `${verb} ${noun}`;
}

export function changedProfileFields(before, after) {
  if (!before || !after) return [];
  return PROFILE_FIELDS.filter(
    ([key]) =>
      Object.hasOwn(before, key) && Object.hasOwn(after, key) && before[key] !== after[key],
  ).map(([, label]) => label);
}

function roleLabel(snapshot) {
  return Object.hasOwn(ROLE_LABELS, snapshot?.ma_vai_tro) ? ROLE_LABELS[snapshot.ma_vai_tro] : null;
}

function employeeDetail(entry, employees) {
  const snapshot = entry.du_lieu_sau ?? entry.du_lieu_truoc;
  const current = employees.find((item) => item.id === Number(entry.doi_tuong_id));
  const code = snapshot?.ma_nhan_vien || current?.ma_nhan_vien || `#${entry.doi_tuong_id}`;
  const name = snapshot?.ho_ten || current?.ho_ten;
  const target = `${code}${name ? ` (${name})` : ""}`;
  const action = formatAuditAction(entry);
  const reason = entry.ly_do ? ` do ${entry.ly_do}` : "";
  const fallback = reason ? `${target}${reason}.` : target;
  if (entry.thao_tac === "dang_nhap") return "Đăng nhập thành công vào hệ thống.";
  if (!snapshot) return fallback;
  if (entry.thao_tac === "tao") {
    const role = roleLabel(snapshot);
    return `Tạo tài khoản ${target}${role ? ` với vai trò "${role}"` : ""}.`;
  }
  if (["cap_quyen", "thu_hoi_quyen"].includes(entry.thao_tac)) {
    const granted = entry.thao_tac === "cap_quyen";
    const role = roleLabel(granted ? entry.du_lieu_sau : entry.du_lieu_truoc);
    if (!role) return fallback;
    const previousRole = roleLabel(entry.du_lieu_truoc);
    const previous =
      granted && previousRole && previousRole !== role ? ` (trước đó: "${previousRole}")` : "";
    return `${granted ? "Gán" : "Thu hồi"} vai trò "${role}" ${granted ? "cho" : "của"} tài khoản ${target}${previous}.`;
  }
  if (["Đổi mật khẩu", "Đặt lại mật khẩu"].includes(action))
    return `${action} tài khoản ${target}.`;
  if (entry.thao_tac === "vo_hieu_hoa" || action === "Mở khóa tài khoản")
    return `${action} ${target}${reason}.`;
  if (entry.thao_tac === "sua") {
    const changed = changedProfileFields(entry.du_lieu_truoc, entry.du_lieu_sau);
    return changed.length
      ? `Cập nhật thông tin tài khoản ${target} (${changed.join(", ")}).`
      : fallback;
  }
  return `${action} ${target}${reason}.`;
}

export function formatAuditDetail(entry, employees = []) {
  if (entry.loai_doi_tuong === "nhan_vien") return employeeDetail(entry, employees);
  const snapshot = entry.du_lieu_sau ?? entry.du_lieu_truoc;
  const fallback = `#${entry.doi_tuong_id}`;
  if (entry.loai_doi_tuong === "vai_tro") {
    const name = snapshot?.ten_vai_tro;
    return `${formatAuditAction(entry)} ${name ? `"${name}"` : fallback}.`;
  }
  const codeField = CODE_FIELDS[entry.loai_doi_tuong];
  const code = snapshot?.[codeField] || entry.du_lieu_truoc?.[codeField] || fallback;
  const noun = OBJECT_LABELS[entry.loai_doi_tuong] || entry.loai_doi_tuong;
  return `${noun} ${code}${entry.ly_do ? ` · ${entry.ly_do}` : ""}`;
}
