# Use-case giai đoạn 1

Danh sách use-case lập từ [BR-GIAIDOAN1](../business_requirements/BR-GIAIDOAN1.md).
Mỗi file nằm tại `use_cases/{bounded_context}/UC-xx.md`; mỗi quy tắc nghiệp vụ trong file ghi rõ BR nguồn.

Tác nhân: Quản trị viên (QTV), Quản lý kho (QLK), Nhân viên (NV).

Các bước dùng chung, không tách thành UC riêng:

- **Kiểm tra quyền truy cập (BR-001)**: chạy trước mọi UC; gõ thẳng đường dẫn không có quyền vẫn bị chặn; tài khoản bị khóa mất quyền ngay.
- **Xác nhận thao tác (BR-015)**: hộp xác nhận cho gửi, duyệt, hoàn tất nhập, kiểm tra có giữ hàng, hủy yêu cầu; hiển thị chứng từ, mặt hàng, số lượng, đơn vị tính, tác động tới kho; đóng hộp thì không có gì thay đổi; chứng từ bị người khác đổi trong lúc xác nhận thì báo và yêu cầu xem lại.
- **Ghi lịch sử thao tác (BR-016)**: ghi người thực hiện, thời điểm, đối tượng, trạng thái trước và sau, lý do; không lưu mật khẩu.

Nguồn "Đề xuất khi lập UC (chưa xác nhận)" đánh dấu quy tắc chưa có trong BR, cần xác nhận.

## `identity_access` — Đăng nhập, phân quyền theo vai trò, quản trị tài khoản

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-01](identity_access/UC-01.md) | Đăng nhập | QTV, QLK, NV | BR-001, BR-016 |
| [UC-02](identity_access/UC-02.md) | Đăng xuất | QTV, QLK, NV | BR-001 |
| [UC-03](identity_access/UC-03.md) | Xem danh sách tài khoản | QTV | BR-002, BR-001 |
| [UC-04](identity_access/UC-04.md) | Thêm tài khoản | QTV | BR-002, BR-016 |
| [UC-05](identity_access/UC-05.md) | Khóa tài khoản | QTV | BR-002, BR-001, BR-016 |
| [UC-06](identity_access/UC-06.md) | Mở khóa tài khoản | QTV | BR-002, BR-016 |
| [UC-07](identity_access/UC-07.md) | Đổi vai trò | QTV | BR-002, BR-016 |
| [UC-08](identity_access/UC-08.md) | Đổi mật khẩu tài khoản | QTV | BR-001, BR-002, BR-016 |

## `catalog` — Danh mục mặt hàng và nhà cung cấp

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-09](catalog/UC-09.md) | Tra cứu mặt hàng | QTV, QLK, NV | BR-003, BR-004 |
| [UC-10](catalog/UC-10.md) | Tạo mặt hàng | QLK | BR-004, BR-005, BR-016 |
| [UC-11](catalog/UC-11.md) | Sửa mặt hàng | QLK | BR-004, BR-010, BR-016 |
| [UC-12](catalog/UC-12.md) | Ngừng / dùng lại thành phẩm | QLK | BR-004, BR-005, BR-007, BR-016 |
| [UC-13](catalog/UC-13.md) | Tra cứu nhà cung cấp | QTV, QLK | BR-003, BR-004 |
| [UC-14](catalog/UC-14.md) | Tạo nhà cung cấp | QLK | BR-004, BR-016 |

## `bom` — Công thức sản phẩm (BOM) một cấp

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-15](bom/UC-15.md) | Xem công thức sản phẩm | QLK, NV | BR-005, BR-003 |
| [UC-16](bom/UC-16.md) | Tạo công thức sản phẩm | QLK | BR-005, BR-016 |
| [UC-17](bom/UC-17.md) | Sửa công thức (tạo phiên bản mới) | QLK | BR-005, BR-016 |
| [UC-18](bom/UC-18.md) | Dùng lại phiên bản công thức cũ | QLK | BR-005, BR-016 |
| [UC-19](bom/UC-19.md) | Ngừng công thức | QLK | BR-005, BR-004, BR-007, BR-016 |

## `goods_receipt` — Nhập kho linh kiện

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-20](goods_receipt/UC-20.md) | Lập, sửa, xóa phiếu nhập nháp | QLK | BR-006, BR-015, BR-016 |
| [UC-21](goods_receipt/UC-21.md) | Hoàn tất phiếu nhập | QLK | BR-006, BR-015, BR-016 |
| [UC-22](goods_receipt/UC-22.md) | Xem phiếu nhập | QLK | BR-006, BR-003 |

## `production` — Yêu cầu sản xuất, kiểm tra và giữ hàng, sản xuất và hoàn thành

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-23](production/UC-23.md) | Lập, sửa, xóa yêu cầu sản xuất nháp | QLK | BR-007, BR-013, BR-015, BR-016 |
| [UC-24](production/UC-24.md) | Gửi yêu cầu sản xuất | QLK | BR-007, BR-005, BR-015, BR-016 |
| [UC-25](production/UC-25.md) | Xem danh sách yêu cầu sản xuất | QLK, NV | BR-007, BR-008, BR-002 |
| [UC-26](production/UC-26.md) | Kiểm tra yêu cầu sản xuất và giữ hàng | NV | BR-008, BR-005, BR-015, BR-016 |
| [UC-27](production/UC-27.md) | Xem nhu cầu bổ sung linh kiện | QLK | BR-009, BR-006 |
| [UC-28](production/UC-28.md) | Hủy yêu cầu sản xuất | QLK | BR-013, BR-015, BR-016 |
| [UC-29](production/UC-29.md) | Bắt đầu sản xuất | NV | BR-011, BR-016 |
| [UC-30](production/UC-30.md) | Lập và gửi chứng từ hoàn thành sản xuất | NV | BR-011, BR-015, BR-016 |
| [UC-31](production/UC-31.md) | Duyệt chứng từ hoàn thành sản xuất | QLK | BR-011, BR-015, BR-016 |
| [UC-32](production/UC-32.md) | Từ chối chứng từ hoàn thành sản xuất | QLK | BR-011, BR-015, BR-016 |
| [UC-33](production/UC-33.md) | Xem danh sách chứng từ hoàn thành sản xuất | QLK | BR-011, BR-014 |

## `goods_issue` — Xuất linh kiện cho sản xuất và xuất thành phẩm

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-34](goods_issue/UC-34.md) | Lập và gửi phiếu xuất linh kiện | NV | BR-010, BR-015, BR-016 |
| [UC-35](goods_issue/UC-35.md) | Duyệt phiếu xuất linh kiện | QLK | BR-010, BR-013, BR-015, BR-016 |
| [UC-36](goods_issue/UC-36.md) | Từ chối phiếu xuất linh kiện | QLK | BR-010, BR-015, BR-016 |
| [UC-37](goods_issue/UC-37.md) | Lập và gửi phiếu xuất thành phẩm | NV | BR-012, BR-010, BR-015, BR-016 |
| [UC-38](goods_issue/UC-38.md) | Duyệt phiếu xuất thành phẩm | QLK | BR-012, BR-015, BR-016 |
| [UC-39](goods_issue/UC-39.md) | Từ chối phiếu xuất thành phẩm | QLK | BR-012, BR-010, BR-015, BR-016 |
| [UC-40](goods_issue/UC-40.md) | Xem danh sách phiếu xuất | QLK | BR-010, BR-012 |

## `reporting` — Báo cáo nhập-xuất-tồn và tra cứu biến động kho

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-41](reporting/UC-41.md) | Xem báo cáo nhập-xuất-tồn | QLK | BR-014 |
| [UC-42](reporting/UC-42.md) | Tra cứu lịch sử biến động kho | QLK | BR-014 |

## `audit` — Lịch sử thao tác

| Mã | Use-case | Tác nhân | BR liên quan |
|---|---|---|---|
| [UC-43](audit/UC-43.md) | Xem lịch sử thao tác | QLK, QTV | BR-016, BR-002 |
