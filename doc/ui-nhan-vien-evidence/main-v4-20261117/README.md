# Kiểm chứng frontend theo main — 17/11/2026

Tham chiếu backend/infra: `origin/main` tại `b228193`. Source UI hiện chưa commit.

| Kiểm tra đã chạy | Kết quả |
| --- | --- |
| `npm.cmd run test` trong frontend | 282 pass, 0 fail, exit 0 |
| `npm.cmd run lint` | Exit 0; [log](./lint.log) |
| `npm.cmd run build` | Exit 0; [log](./build.log) |
| Playwright 8 file trong lượt cuối | 84 pass, 0 fail, 3.3 phút, exit 0; [log](./browser.log) |

Lệnh Playwright: `npx.cmd playwright test tests/browser/employee-ui.spec.js tests/browser/employee-request-filters.spec.js tests/browser/issue-main-flow.spec.js tests/browser/navigation.spec.js tests/browser/sidebar.spec.js tests/browser/workflows.spec.js tests/browser/record-dialog.spec.js tests/browser/admin-ui.spec.js`.

[Lượt đầu](./browser-first.log) có 6 lỗi do test còn dùng đường dẫn/nút/nhãn cũ, không phải kết quả cuối. Các test được cập nhật theo luồng đã thống nhất; giữ kiểm tra ETag, lỗi, hủy xác nhận, focus và phân quyền. Fixture từ chối danh sách QLK-only cho NV, schema tạo phiếu chỉ hai trường, không hỗ trợ PATCH/DELETE/ve_nhap.

Đây là kiểm chứng frontend với API fixture, không xác nhận DB/transaction hay phân quyền runtime backend. NV-MAIN-005/006 còn mở; tham khảo [MISSING](../../MISSING.md) và [ảnh sau sửa](../../ui-nhan-vien-screenshots/2026-11-17-main-fixed/README.md). Không chạy API thật/DB/SQL/seed/reset trong lượt sửa này.
