import { canAccessPath } from "../features/auth/permissions.js";

const navigation = {
  quan_tri_vien: [
    {
      title: "Quản trị",
      items: [
        ["/admin", "Tổng quan"],
        ["/admin/tai-khoan", "Quản lý tài khoản"],
        ["/admin/vai-tro", "Quản lý vai trò"],
      ],
    },
  ],
  quan_ly: [
    { title: "Chung", items: [["/kho", "Tổng quan"]] },
    {
      title: "Danh mục",
      items: [
        ["/kho/mat-hang", "Mặt hàng & tồn kho"],
        ["/kho/nha-cung-cap", "Nhà cung cấp"],
        ["/kho/bom", "Định mức BOM"],
      ],
    },
    {
      title: "Vận hành",
      items: [
        ["/kho/phieu-nhap", "Phiếu nhập kho"],
        ["/kho/nhu-cau-bo-sung", "Nhu cầu bổ sung LK"],
        ["/kho/yeu-cau", "Yêu cầu sản xuất"],
        ["/kho/phieu-xuat", "Phiếu xuất kho"],
        ["/kho/chung-tu-hoan-thanh", "Hoàn thành sản xuất"],
      ],
    },
    {
      title: "Theo dõi",
      items: [
        ["/kho/thong-ke", "Nhập – xuất – tồn"],
        ["/kho/giao-dich", "Biến động kho"],
      ],
    },
  ],
  nhan_vien: [
    { title: "Chung", items: [["/nv", "Tổng quan"]] },
    {
      title: "Sản xuất",
      items: [
        ["/nv/yeu-cau", "Việc được giao"],
      ],
    },
    {
      title: "Theo dõi",
      items: [["/nv/ton-kho", "Tra cứu tồn kho"]],
    },
  ],
};

export function navigationFor(role) {
  if (!Object.hasOwn(navigation, role)) return [];
  return navigation[role]
    .map((group) => ({
      ...group,
      items: group.items.filter(([path]) => canAccessPath(role, path)),
    }))
    .filter((group) => group.items.length > 0);
}
