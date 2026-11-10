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
      title: "Quản lý kho",
      items: [
        ["/kho/mat-hang", "Mặt hàng và tồn kho"],
        ["/kho/nha-cung-cap", "Nhà cung cấp"],
        ["/kho/phieu-nhap", "Phiếu nhập kho"],
        ["/kho/giao-dich", "Giao dịch kho"],
      ],
    },
    {
      title: "Sản xuất",
      items: [
        ["/kho/bom", "BOM"],
        ["/kho/yeu-cau", "Yêu cầu thành phẩm"],
        ["/kho/lenh-sx", "Lệnh sản xuất"],
        ["/kho/phieu-xuat", "Phiếu xuất kho"],
        ["/kho/duyet-hoan-thanh", "Duyệt chứng từ hoàn thành SX"],
      ],
    },
    {
      title: "Kiểm soát",
      items: [
        ["/kho/dieu-chinh", "Điều chỉnh kho"],
        ["/kho/ticket", "Ticket sự cố"],
        ["/kho/thong-ke", "Thống kê nhập – xuất – tồn"],
        ["/kho/lich-su", "Lịch sử thao tác"],
      ],
    },
  ],
  nhan_vien: [
    { title: "Chung", items: [["/nv", "Tổng quan"]] },
    {
      title: "Sản xuất",
      items: [
        ["/nv/lenh-sx", "Việc được giao"],
        ["/nv/hoan-thanh", "Chứng từ hoàn thành SX"],
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
