export const navigation = {
  quan_tri_vien: [
    { title: "Chung", items: [["/admin", "Tổng quan"]] },
    {
      title: "Quản trị",
      items: [
        ["/admin/tai-khoan", "Tài khoản"],
        ["/admin/vai-tro", "Vai trò"],
        ["/admin/lich-su", "Lịch sử thao tác"],
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
    { title: "Chung", items: [["/nv", "Việc được giao"]] },
    {
      title: "Sản xuất",
      items: [
        ["/nv/yeu-cau", "Yêu cầu phụ trách"],
        ["/nv/lenh-sx", "Lệnh của tôi"],
        ["/nv/xuat-nvl", "Phiếu xuất NVL / BTP"],
        ["/nv/xuat-tp", "Phiếu xuất thành phẩm"],
        ["/nv/hoan-thanh", "Chứng từ hoàn thành SX"],
      ],
    },
    {
      title: "Theo dõi",
      items: [
        ["/nv/phieu", "Phiếu của tôi"],
        ["/nv/ton-kho", "Tra cứu tồn kho"],
      ],
    },
  ],
};
