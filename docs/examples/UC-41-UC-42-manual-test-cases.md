# Testcase API reporting — UC-41 và UC-42

Ngày lập: 16/11/2026. Phạm vi BR-014, data model v4; đối chiếu `backend/app/modules/reporting/{router,schemas,service,repository}.py`, spec UC-41/UC-42 và các test tương ứng. Đây là **bộ hướng dẫn kiểm thử**, không phải báo cáo đã chạy đủ các case trên DB thật.

## 1. Chuẩn bị

- Backend: `http://localhost:8000`; Swagger: `http://localhost:8000/docs`.
- Database phải có schema v4. Không nạp lại seed hoặc sửa lịch sử trên DB đang có dữ liệu để thực hiện bộ testcase.
- Chuẩn bị token QLK (`quan_ly`), QTV (`quan_tri_vien`), NV (`nhan_vien`); các API reporting chỉ cho QLK.
- Ví dụ đăng nhập bằng API JSON:

```http
POST /api/v1/auth/dang_nhap
Content-Type: application/json

{
  "ten_dang_nhap": "quan_ly_kho",
  "mat_khau": "<mat_khau_cua_tai_khoan>"
}
```

Lấy `data.access_token` và gửi header sau cho từng request GET:

```http
Authorization: Bearer <token>
```

Các GET không có request body và không yêu cầu `If-Match`.

Ký hiệu dùng trong bảng:

| Ký hiệu | Cách chọn |
|---|---|
| `<MH>` | ID mặt hàng có giao dịch, chọn từ `GET /api/v1/mat_hang?page=1&page_size=100` hoặc từ kết quả lịch sử |
| `<NV>` | ID người ghi nhận giao dịch, lấy từ `nhan_vien.id` của một dòng lịch sử |
| `<ID_KHONG_CO>` | ID dương đã xác minh không tồn tại; không mặc định rằng 999 hoặc một ID cố định luôn vắng mặt |
| `<MH_TP>` | ID mặt hàng có `loai_mat_hang=thanh_pham` |

Nếu đăng nhập lỗi 500, kiểm tra traceback/schema trước; chưa coi đó là kết quả của testcase reporting. Với các case kiểm quyền, luôn dùng query hợp lệ để không trộn lỗi xác thực với lỗi đầu vào.

## 2. Request mẫu chạy nhanh

### UC-41 — Báo cáo nhập–xuất–tồn

```http
GET /api/v1/bao_cao/nhap_xuat_ton?ky=thang&nam=2026&thang=11
GET /api/v1/bao_cao/nhap_xuat_ton?ky=quy&nam=2026&quy=4
GET /api/v1/bao_cao/nhap_xuat_ton?ky=nam&nam=2026
GET /api/v1/bao_cao/nhap_xuat_ton?ky=thang&nam=2026&thang=11&mat_hang_id=<MH>&loai_mat_hang=linh_kien
```

Kết quả thành công: HTTP **200**, `success=true`, `data.mat_hang` là mảng; mỗi dòng có `mat_hang_id`, `ma_mat_hang`, `ten_mat_hang`, `loai_mat_hang`, `don_vi_tinh`, `ton_dau_ky`, `nhap_trong_ky`, `xuat_trong_ky`, `ton_cuoi_ky`. API này **không phân trang**. `xuat_trong_ky` là lượng xuất dương, không phải số âm.

### UC-42 — Lịch sử biến động kho

```http
GET /api/v1/bao_cao/bien_dong_kho?page=1&page_size=20
GET /api/v1/bao_cao/bien_dong_kho?mat_hang_id=<MH>
GET /api/v1/bao_cao/bien_dong_kho?loai_giao_dich=nhap_linh_kien
GET /api/v1/bao_cao/bien_dong_kho?mat_hang_id=<MH>&nhan_vien_id=<NV>&tu_ngay=2026-11-01&den_ngay=2026-11-30&page=1&page_size=20
```

Kết quả thành công: HTTP **200**, `success=true`, `data` là mảng; `pagination` có `page`, `page_size`, `total_items`, `total_pages`, `has_next`, `has_prev`. Mỗi dòng có `id`, `posted_at`, `loai_giao_dich`, `so_luong_bien_dong`, `so_luong_ton_sau`, và ba object `mat_hang`, `chung_tu`, `nhan_vien`.

## 3. Xác thực và phân quyền — áp dụng cho cả hai API

Với UC-41, dùng query hợp lệ `ky=thang&nam=2026&thang=11`; UC-42 có thể không truyền query. Mỗi dòng dưới đây cần thử trên **cả hai endpoint**.

| ID | Điều kiện / thao tác | HTTP mong đợi | Kiểm tra thêm |
|---|---|---|---|
| AUTH-01 | Token QLK còn hạn, tài khoản hoạt động | 200 | Đúng cấu trúc response; dữ liệu thuộc bộ lọc |
| AUTH-02 | Bỏ hoàn toàn header Authorization | 401 | Không có dữ liệu báo cáo/lịch sử trong response |
| AUTH-03 | `Authorization: Bearer invalid-token` | 401 | Không trả 500 hoặc dữ liệu nghiệp vụ |
| AUTH-04 | Token đã hết hạn thực sự | 401 | Dùng token hết hạn hợp lệ; sửa chuỗi JWT chỉ kiểm được lỗi token/chữ ký |
| AUTH-05 | Token QTV còn hạn | 403 | QTV không được đọc reporting |
| AUTH-06 | Token NV còn hạn | 403 | NV không được đọc reporting |
| AUTH-07 | Token của QLK đã được khóa tài khoản trên môi trường test | 403 | Khóa trước khi request, bảo đảm token chưa hết hạn; không dùng tài khoản vận hành để dựng case |

## 4. UC-41 — Báo cáo nhập–xuất–tồn

Base path: `/api/v1/bao_cao/nhap_xuat_ton`. Dùng token QLK.

Các biến thể trong cùng một dòng phải chạy **từng request độc lập**.

| ID | Query / điều kiện | HTTP | Kết quả mong đợi |
|---|---|---|---|
| BC-01 | `ky=thang&nam=2026&thang=11` | 200 | Biên `[2026-11-01T00:00:00+07:00, 2026-12-01T00:00:00+07:00)`; có đủ bốn chỉ tiêu tồn đầu/nhập/xuất/tồn cuối |
| BC-02 | `ky=quy&nam=2026&quy=4` | 200 | Biên từ 01/10/2026 đến trước 01/01/2027 giờ Việt Nam |
| BC-03 | `ky=nam&nam=2026` | 200 | Biên từ 01/01/2026 đến trước 01/01/2027 giờ Việt Nam |
| BC-04 | BC-01 + `mat_hang_id=<MH>` | 200 | Chỉ có mặt hàng đã chọn |
| BC-05 | BC-01 + `loai_mat_hang=linh_kien`; thử riêng `thanh_pham` | 200 | Mọi dòng đúng loại đã chọn |
| BC-06 | BC-01 + `mat_hang_id=<MH_TP>&loai_mat_hang=linh_kien` | 200 | `data.mat_hang=[]`; hai bộ lọc kết hợp AND |
| BC-07 | BC-01 + `mat_hang_id=<ID_KHONG_CO>` | 200 | Mảng mặt hàng rỗng, không trả 404 |
| BC-08 | Lọc mặt hàng đã ngừng sử dụng nhưng có lịch sử kho — cần fixture | 200 | Vẫn tra cứu được lịch sử của mặt hàng đó |
| BC-09 | Lọc mặt hàng chưa từng có ledger — cần fixture | 200 | Có dòng mặt hàng, cả bốn chỉ tiêu bằng 0 |
| BC-10 | Có chứng từ nháp/chờ duyệt/từ chối, chưa có ledger — cần fixture | 200 | Những chứng từ đó không làm đổi bốn chỉ tiêu |
| BC-11 | Bỏ `ky`; bỏ `nam`; kỳ tháng thiếu `thang`; kỳ quý thiếu `quy` | 422 | Mỗi biến thể đều bị từ chối, không trả kết quả thành công |
| BC-12 | `ky=tuan&nam=2026` | 422 | Chỉ chấp nhận `thang`, `quy`, `nam` |
| BC-13 | Kỳ năm kèm `thang`; kỳ năm kèm `quy`; kỳ tháng kèm `quy`; kỳ quý kèm `thang` | 422 | Không chấp nhận tham số kỳ không liên quan; vẫn điền đủ các tham số bắt buộc khác |
| BC-14 | Tháng 0/13; quý 0/5 | 422 | Tháng chỉ 1–12, quý chỉ 1–4 |
| BC-15 | BC-01 nhưng `nam=1`; thử `nam=9999` | 422 | Schema hiện nhận năm 2–9998 |
| BC-16 | BC-01 + `mat_hang_id=0`, `-1`, `abc` | 422 | ID phải là số nguyên dương |
| BC-17 | BC-01 + `loai_mat_hang=ban_thanh_pham` | 422 | Schema v4 reporting chỉ nhận `linh_kien`/`thanh_pham` |
| BC-18 | BC-01 + `page=1`; thử riêng `extra=abc` | 422 | Cấm query ngoài schema; API báo cáo không có phân trang |

## 5. UC-42 — Lịch sử biến động kho

Base path: `/api/v1/bao_cao/bien_dong_kho`. Dùng token QLK.

| ID | Query / điều kiện | HTTP | Kết quả mong đợi |
|---|---|---|---|
| BD-01 | Không có query | 200 | Mặc định `page=1`, `page_size=20`; mới nhất trước |
| BD-02 | `mat_hang_id=<MH>` | 200 | Mọi dòng có `mat_hang.id=<MH>`; chứng từ gốc tương ứng đúng mặt hàng |
| BD-03 | Lần lượt từng loại giao dịch trong bảng dưới | 200 | Mọi dòng đúng loại; không có loại khác lẫn vào |
| BD-04 | `nhan_vien_id=<NV>` | 200 | Mọi dòng có `nhan_vien.id=<NV>`; đây là người ghi nhận trong ledger |
| BD-05 | `mat_hang_id=<MH>&nhan_vien_id=<NV>&loai_giao_dich=nhap_linh_kien&tu_ngay=2026-11-01&den_ngay=2026-11-30` | 200 | Mọi dòng đồng thời thỏa cả năm điều kiện, không kết hợp OR |
| BD-06 | Chỉ `tu_ngay=2026-11-01`; thử riêng chỉ `den_ngay=2026-11-30` | 200 | Chấp nhận khoảng ngày chỉ có một đầu; áp dụng đúng đầu đã gửi |
| BD-07 | `mat_hang_id=<ID_KHONG_CO>`; thử ID nhân viên không có | 200 | `data=[]`, `total_items=0`, `total_pages=0`, `has_next=false`, `has_prev=false` khi page mặc định 1 |
| BD-08 | `page=1&page_size=2`, sau đó `page=2&page_size=2` — ít nhất 3 dòng, ngừng ghi mới khi so sánh | 200 | Không trùng ID giữa hai trang; tổng số dòng nhất quán; trang đầu `has_prev=false` |
| BD-09 | Trang lớn hơn `total_pages`, dùng số vừa phải | 200 | `data=[]`; giữ `total_items` của toàn bộ kết quả, không biến tổng thành 0 |
| BD-10 | Hai dòng trùng `posted_at` — cần fixture | 200 | Dòng có `id` lớn hơn đứng trước; phân trang vẫn ổn định khi không có ghi mới |
| BD-11 | Có đủ các loại nhập/xuất — cần dữ liệu phù hợp | 200 | Lượng nhập dương, lượng xuất âm; `so_luong_ton_sau` là snapshot đã lưu; object mặt hàng/chứng từ/nhân viên đủ trường |
| BD-12 | Chứng từ từ chối/chưa ghi sổ, không có ledger — cần fixture | 200 | Không xuất hiện trong kết quả |
| BD-13 | `loai_giao_dich=nhap`; thử `xuat_vat_tu` | 422 | Không nhận mã tự đặt hoặc mã v3 |
| BD-14 | `mat_hang_id` hoặc `nhan_vien_id` lần lượt là 0, -1, `abc` | 422 | Cả hai loại ID đều phải là số nguyên dương |
| BD-15 | `tu_ngay=16/11/2026`; ngày không tồn tại `den_ngay=2026-02-30`; gửi datetime `tu_ngay=2026-11-01T00:00:00Z` | 422 | Chỉ nhận ngày hợp lệ dạng `YYYY-MM-DD` |
| BD-16 | `tu_ngay=2026-12-01&den_ngay=2026-11-01`; thử riêng `tu_ngay=0001-01-01` hoặc `den_ngay=9999-12-31` | 422 | Chặn khoảng đảo ngược và hai biên ngày có thể gây tràn khi đổi UTC/tính ngày kế tiếp |
| BD-17 | `page=0`, `page=-1`, `page_size=0`, `page_size=101` | 422 | `page>=1`, `1<=page_size<=100` |
| BD-18 | `sort_by=id`; thử riêng `extra=abc` | 422 | Thứ tự sắp xếp được cố định, không nhận query ngoài schema |

Các mã loại giao dịch hợp lệ:

| `loai_giao_dich` | Dấu số lượng | `chung_tu.loai` |
|---|---|---|
| `nhap_linh_kien` | Dương | `phieu_nhap` |
| `xuat_linh_kien` | Âm | `phieu_xuat` |
| `nhap_san_pham_san_xuat` | Dương | `chung_tu_hoan_thanh_sx` |
| `xuat_thanh_pham` | Âm | `phieu_xuat` |

`posted_at` có thể được API trả về UTC (`Z`); không yêu cầu chuỗi response phải có `+07:00`. Đối chiếu cùng một thời điểm sau khi đổi múi giờ.

## 6. Đối soát số liệu và biên thời gian

Các case dưới đây cần fixture trên **DB test/demo đã được cho phép**, với một mặt hàng riêng, không có giao dịch khác. Không sửa thời gian hệ thống hoặc `posted_at` của dữ liệu đang sử dụng. Có thể giao người chuẩn bị fixture dựng dữ liệu này; Swagger không tự tạo được các giao dịch lịch sử chỉ bằng cách gọi hai GET reporting.

| Giao dịch | Thời điểm giờ Việt Nam | Biến động | Tồn sau |
|---|---|---|---|
| GD-A | `2025-12-31T23:59:59+07:00` | +100 | 100 |
| GD-B | `2026-01-01T00:00:00+07:00` | +30 | 130 |
| GD-C | `2026-01-31T23:30:00+07:00` | -20 | 110 |
| GD-D | `2026-02-01T00:00:00+07:00` | +7 | 117 |

Các dòng ledger phải có nguồn chứng từ hợp lệ và đúng trạng thái đã ghi nhận; số tồn thực tế của mặt hàng trong fixture là 117. Chỉ lọc mặt hàng fixture khi so sánh.

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| CK-01 | Báo cáo tháng 1/2026 | Tồn đầu **100**, nhập **30**, xuất **20**, tồn cuối **110**; `100+30-20=110` |
| CK-02 | Báo cáo tháng 2/2026 | Tồn đầu **110**, nhập **7**, xuất **0**, tồn cuối **117**; tồn đầu tháng 2 bằng tồn cuối tháng 1 |
| CK-03 | Tra cứu ngày `tu_ngay=2026-01-31&den_ngay=2026-01-31` | Có GD-C, không có GD-D; khoảng UTC là `[2026-01-30T17:00:00Z, 2026-01-31T17:00:00Z)` |
| CK-04 | Báo cáo tháng 3/2026, fixture không có ghi mới sau GD-D | Tồn đầu/cuối đều **117**, nhập/xuất đều **0**; không lấy số dư 0 chỉ vì kỳ không có giao dịch |
| CK-05 | Sau khi đăng nhập, ghi nhận dữ liệu trước/sau nhiều lần gọi hai GET | Số dòng ledger/audit, số dư/giữ hàng và trạng thái chứng từ không đổi; không ghi audit cho hành vi đọc reporting |

CK-05: lấy mốc **sau đăng nhập** vì đăng nhập có thể ghi audit. Không dùng số đếm request trong `LuuLuongTruyCap` để kết luận GET reporting sửa dữ liệu nghiệp vụ: middleware có thể cập nhật số đếm này bình thường. Tránh tác vụ ghi đồng thời khi so sánh.

## 7. Ghi nhận kết quả

Với từng ID, ghi: môi trường/phiên bản code, query thực gửi, vai trò, HTTP thực tế, dữ liệu quan sát, Pass/Fail/Chưa kiểm chứng. Mỗi biến thể đầu vào là một lượt chạy. HTTP 200 chỉ chứng minh request thành công, chưa đủ để kết luận số liệu đúng nếu chưa đối chiếu.

Nếu API trả 500: lưu response và traceback đã che thông tin nhạy cảm, đánh dấu Fail; không coi lỗi 500 là một kết quả hợp lệ thay cho 422 hoặc danh sách rỗng.

Mẫu ghi kết quả:

| TC ID / biến thể | Vai trò | Query | HTTP thực tế | Quan sát | Kết quả |
|---|---|---|---|---|---|
| BC-01 | QLK | `ky=thang&nam=2026&thang=11` | … | Biên kỳ và bốn chỉ tiêu: … | Chưa chạy |

## 8. Chạy bộ kiểm thử API tự động có sẵn

Hai file sau dùng repository giả qua ASGI/JWT để kiểm tra hành vi API, không thay cho SQL thật hoặc toàn bộ E2E:

```powershell
cd D:\xbike-mrp-system\backend
& ..\.venv\Scripts\python.exe -m pytest tests/test_uc41_bao_cao_nhap_xuat_ton.py tests/test_uc42_bien_dong_kho.py -q
```

Các test PostgreSQL riêng là `test_uc41_bao_cao_postgres.py`, `test_uc42_bien_dong_kho_postgres.py`. Chỉ cấu hình URL và chạy khi đã xác nhận đúng DB test/demo. Không lấy URL DB ứng dụng để chạy toàn bộ test một cách mặc định: nhóm audit có case commit thật và để lại dữ liệu.

## 9. Truy vết tài liệu

- [UC-41](../../specs/use_cases/reporting/UC-41.md): BC-01…BC-18, AUTH-01…AUTH-07, CK-01/02/04/05; AC-1 đối soát tồn, AC-2 chứng từ chưa ghi nhận, AC-3 giờ Việt Nam, AC-4 nối kỳ.
- [UC-42](../../specs/use_cases/reporting/UC-42.md): BD-01…BD-18, AUTH-01…AUTH-07, CK-03/05; AC-1 mặt hàng và chứng từ gốc, AC-2 không gồm phiếu từ chối, AC-3 loại nghiệp vụ.
- [Sequence reporting](../sequence/reporting.md), [plan UC-41](../plans/UC-41.md), [plan UC-42](../plans/UC-42.md).
