# Các phần còn thiếu khi triển khai frontend

Theo dõi các thành phần trong thiết kế mà API hoặc thông tin đã chốt chưa đáp ứng. Tuân thủ [quy tắc frontend](./FRONTEND_RULES.md); tiếp tục các phần độc lập đã rõ, hỏi dev về phần chưa rõ và không tự bổ sung chức năng.

File được khởi tạo cùng quy tắc frontend và được cập nhật trong đợt triển khai Admin UI (`feature/UI-admin`). Các khác biệt admin đã ghi trong [đặc tả giao diện admin](./dac-ta-giao-dien-admin.md) là căn cứ để đối chiếu khi triển khai.

## Danh sách

- [x] FE-MISS-001 — Lưu lượng truy cập website theo giờ và bộ lọc khoảng thời gian
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-01 Tổng quan (`OV-03`, `OV-04`, `OV-Q01`) — `tong_quan.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Khối “Lưu lượng truy website”, bộ chọn `Hôm nay` / `7 ngày` / `30 ngày` và đường biểu diễn số lượng request theo giờ.
  - Thiết kế yêu cầu: Hiển thị biểu đồ đường màu cam kèm vùng tô phía dưới theo số lượng request mỗi giờ (`00h` đến `21h`) và chuyển đổi dữ liệu theo `Hôm nay`, `7 ngày`, `30 ngày`.
  - API hiện đáp ứng / còn thiếu: Backend hiện chỉ có các endpoint `/auth/*`, `/nhan_vien`, `/vai_tro`, `/audit` và các module nghiệp vụ kho/sản xuất; chưa có endpoint thống kê lưu lượng HTTP request hoặc metrics truy cập theo khung thời gian.
  - Bằng chứng: `frontend/src/lib/api/endpoints.js`, `backend/app/modules/nhan_vien/router.py`, `backend/app/modules/audit/router.py`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Đã dựng đầy đủ khung thẻ “Lưu lượng truy website”, dòng mô tả “Tổng hợp theo số lượng request mỗi giờ”, trục tọa độ và 3 nút `Hôm nay` / `7 ngày` / `30 ngày` đúng hình thức ảnh nhưng chưa gắn hành động gọi API và không vẽ đường/số liệu giả.
  - Câu hỏi / quyết định cần dev xác nhận: Nguồn thu thập số liệu request, hợp đồng API trả về chuỗi thời gian, múi giờ tổng hợp và bước thời gian cho chế độ `7 ngày` / `30 ngày`.
  - Phản hồi của dev: Đợt UI admin trước đó, dev đã chốt trong `doc/admin-ui-plan.md` giữ khung và các nút chưa gắn hành động. Ngày 09/11/2026, dev chốt cho backend tuân theo frontend và duyệt `.handoff/plan-luu-luong-truy-cap.md`. Nội dung đã chốt (ghi tại `docs/DECISION.md` D-LL-01):
    - số liệu lưu vào bảng `"LuuLuongTruyCap"` theo từng giờ;
    - `Hôm nay` có 24 điểm theo giờ, nhãn hiện mỗi 3 giờ;
    - `7 ngày` có 7 điểm theo ngày;
    - `30 ngày` có 30 điểm theo ngày, kèm đường trung bình trượt 7 ngày và chú giải;
    - luôn hiện hôm nay với số đếm đến hiện tại;
    - trục Y tuyến tính, tối thiểu 4.000;
    - dòng mô tả đổi giữa "mỗi giờ" và "mỗi ngày" theo bộ lọc.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục:
    - Backend: thêm module `backend/app/modules/luu_luong/` (middleware đếm request, `GET /api/v1/luu_luong_truy_cap` chỉ cho `quan_tri_vien`) và bảng mới trong `infra/postgres/init.sql`. Kiểm tra bằng `backend/tests/test_luu_luong_api.py`, 14/14 test qua trên DB `xbike_mrp_test`.
    - Frontend: gắn 3 nút vào API và vẽ đường cam có vùng tô trong `DashboardPage.jsx` (`TrafficCard`). Test `frontend/tests/browser/admin-ui.spec.js` (ADM-01) qua.
    - Tài liệu: `docs/sequence/luu_luong.md`, `docs/api_contract_v3.md` §3 và §13.
    - Giới hạn: database đang chạy chưa có bảng mới cho tới khi khởi tạo lại từ `init.sql`.

- [x] FE-MISS-002 — Trường mô tả vai trò và phạm vi Tạo / Sửa / Xóa vai trò
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-04 Quản lý vai trò (`ROL-03`, `ROL-04`, `ROL-05`, `ROL-06`, `ROL-Q01`..`ROL-Q04`) — `quan_ly_vai_tro.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Cột “Mô tả” trong bảng vai trò; nút `+ Tạo vai trò`; nút `Sửa` và nút `Xóa` trên từng dòng vai trò.
  - Thiết kế gốc: Hiển thị mô tả cho từng vai trò và thao tác tạo/sửa/xóa. Phạm vi đã được dev điều chỉnh tại D-VT-01 (09/11/2026).
  - API hiện đáp ứng: `GET /api/v1/vai_tro` trả `VaiTroRead` gồm `id`, `ma_vai_tro`, `ten_vai_tro`, `mo_ta` (`string | null`); admin/quản lý được đọc, nhân viên nhận 403. Không hỗ trợ API ghi vai trò vì bộ vai trò cố định theo SRS_v4 §2.
  - Bằng chứng: `backend/app/modules/nhan_vien/models.py`, `schemas.py`, `router.py`; `infra/postgres/init.sql`, `seed.sql`; `docs/api_contract_v3.md` §4; `docs/sequence/nhan_vien.md`.
  - Hành vi đã triển khai: ADM-04 hiển thị mô tả từ API, null hiển thị `—`, tìm theo mô tả; nút `+ Tạo vai trò` disabled và mờ 0.55; giữ Sửa/Xóa vô hiệu hóa theo mã của ba vai trò hệ thống, kèm icon thông tin.
  - Quyết định đã chốt: Không mở CRUD vai trò động hoặc thay cơ chế phân quyền; không có form tạo/sửa/xóa.
  - Phản hồi của dev: Duyệt `.handoff/plan-vai-tro-mo-ta.md`: (1) giữ ba vai trò cố định, mô tả chỉ đọc; (2) giữ Sửa vô hiệu hóa; (3) seed theo SRS_v4 §2; (4) cột `mo_ta varchar(255) NULL`; (5) Tạo disabled và mờ; (6) đóng FE-MISS-002 và ghi D-VT-01, đóng ROL-Q01..Q04. Trong phiên triển khai, dev chọn test backend tạm và đồng ý kiểm tra UI trực tiếp thay hai skill ui-consistency không có sẵn.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: 14/14 ca backend tạm đạt trên PostgreSQL test riêng, bao gồm mô tả/null, quyền 401/403, ghi trả 405, phân trang, đăng nhập và hồ sơ; bootstrap nguyên bản init/seed thành công trên container tạm, ba mô tả dài 135/136/124 ký tự. Playwright ADM-04 đạt: mô tả đúng, tìm “BOM” còn Quản lý kho, null hiện `—`, Tạo disabled và không phát sinh request. Đóng theo D-VT-01, không phải xác nhận chức năng ghi vai trò đã được bổ sung.
  - Giới hạn triển khai: Chưa thay đổi DB ứng dụng; backend mới cần cột `mo_ta`, nếu DB cũ thiếu cột thì đăng nhập và mọi request có token có thể trả 500. Chỉ bootstrap DB mới/trống, không migration. Contract/data model trên Drive cần dev cập nhật riêng.

- [ ] FE-MISS-003 — Ảnh đại diện (avatar) nhân viên
  - Màn hình / mã yêu cầu / ảnh thiết kế: Khung dùng chung (`LAY-08`), ADM-02 Quản lý tài khoản (`ACC-04`), ADM-03 Chi tiết tài khoản (`DET-04`, `DET-Q03`) — `quan_ly_tai_khoan.png`, `chi_tiet_tai_khoan.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Avatar tròn ở góc trên bên phải, trong cột “Tên” của bảng tài khoản và trong thẻ nhận diện bên trái trang chi tiết tài khoản.
  - Thiết kế yêu cầu: Hiển thị ảnh chân dung tròn của người dùng/nhân viên.
  - API hiện đáp ứng / còn thiếu: `NhanVienRead` và `NhanVienAssignmentRead` không có trường URL/định danh ảnh đại diện và backend không có endpoint tải ảnh lên.
  - Bằng chứng: `backend/app/modules/nhan_vien/schemas.py` (`NhanVienAssignmentRead`, `NhanVienRead`, dòng 56–76).
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Hiển thị avatar tròn với chữ cái viết tắt từ họ tên/tên đăng nhập (`initials`), không dùng ảnh người giả và không tự thêm tính năng upload.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung trường ảnh đại diện vào hồ sơ nhân viên trong các giai đoạn sau hay giữ avatar chữ cái.
  - Phản hồi của dev: Dev đã chốt trong `doc/admin-ui-plan.md` dùng avatar chữ cái hiện có khi chưa có ảnh nhân viên, không thêm upload ảnh hoặc dùng ảnh người giả.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Đã áp dụng đồng bộ trên header, danh sách và chi tiết tài khoản; giữ `[ ]` đối với trường dữ liệu ảnh đại diện từ API.

- [x] FE-MISS-004 — Nội dung chi tiết sự kiện trong bảng Hoạt động gần đây cho vai trò Quản trị viên
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-01 Tổng quan (`OV-07`, `OV-08`, `OV-Q03`) — `tong_quan.png`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Cột “Hành động” và “Chi tiết” của bảng “Hoạt động gần đây”.
  - Thiết kế yêu cầu: Hiển thị câu mô tả giàu ngữ cảnh nghiệp vụ (ví dụ tên đối tượng được tạo/cập nhật hoặc chi tiết thay đổi cụ thể).
  - API sau triển khai: Theo D-HD-01, admin và quản lý nhận `AuditLogResponse` đầy đủ hai key snapshot (`object | null`) ở mọi loại đối tượng; nhân viên vẫn 403. Query `bo_thao_tac` nhận một thao tác hợp lệ (gồm `dang_nhap`), enum sai 422, filter trước COUNT/phân trang; admin sort JSON giống quản lý. Giữ route/envelope/query legacy hiện hành.
  - Bằng chứng: `backend/app/modules/audit/{schemas,service,router,ports,repository}.py`; `auth/service.py`, `nhan_vien/service.py` ghi đúng một audit `dang_nhap`, transaction commit xong mới cấp token ở cả hai endpoint đăng nhập; lỗi append/commit trả 500, không cấp token; đăng nhập bị từ chối không ghi audit.
  - Frontend sau verify lần 1: `DashboardPage.jsx` gửi `bo_thao_tac=thu_hoi_quyen` riêng ADM-01, giữ query kho; dùng `auditFormat.js` export `changedProfileFields`, `formatAuditAction`, `formatAuditDetail`. `frontend/tests/contracts.test.js` đã commit là đặc tả ưu tiên, được giữ nguyên. Mã/họ tên ưu tiên snapshot rồi danh sách nhân viên rồi `#id`; câu có họ tên sau mã, Tạo có vai trò nếu biết; Phân quyền dùng `ma_vai_tro` lịch sử và thêm vai trò trước đó nếu biết. Nhãn dùng chung `ROLE_LABELS` trong `lib/format.js`, không cần query danh sách vai trò cho helper. Chỉ liệt kê tên trường hồ sơ đã đổi có mặt ở cả hai snapshot, không hiện giá trị; thiếu snapshot/vai trò trả về định danh tài khoản, không bịa lịch sử. Đổi/đặt lại mật khẩu dùng cùng văn phong kèm mã/họ tên. Trang `/admin/lich-su` vẫn render khi API thêm hai key, giữ nguyên UI của trang đó.
  - Phản hồi dev (10/11/2026): Thực hiện D-HD-01 từ `api_contract_v3.1.md` trên Google Drive của project (§4 D-HD-01, §13 GET /lich_su_thao_tac), Claude đọc ngày 10/11/2026; dùng bộ UI đã commit, xóa đúng bộ UI untracked trong Bước 0; chỉ chạy tạm test backend rồi xóa; giữ test frontend; không làm FE-MISS-005.
  - Kết quả kiểm thử backend: `cd backend; .venv/Scripts/python.exe -m pytest tests/test_tam_fe_miss_004.py -q` đạt **90/90**, không DB. Đã ghi kết quả rồi xóa `test_tam_fe_miss_004.py`; giữ nguyên test có sẵn `test_nhan_vien_create_code.py`. `.venv/Scripts/python.exe -m ruff check` và `-m ruff format --check` trên 7 file Python sửa: đạt.
  - Gói đã cài vào `backend/.venv` để chạy kiểm thử: **39 gói** dưới đây, gồm cả phụ thuộc; không sửa manifest/lockfile (`pip` đã có sẵn, không cài lại):
    - `colorama==0.4.6`, `iniconfig==2.3.1`, `packaging==26.3`, `pluggy==1.7.0`, `Pygments==2.21.0`, `pytest==9.1.1`, `pytest-asyncio==1.4.0`, `ruff==0.17.1`, `typing_extensions==4.16.0`.
    - `annotated-doc==0.0.5`, `annotated-types==0.8.0`, `anyio==4.15.1`, `fastapi==0.144.0`, `pydantic==2.14.1`, `pydantic_core==2.50.1`, `starlette==1.8.0`, `typing-inspection==0.4.4`, `SQLAlchemy==2.1.5`, `greenlet==3.5.6`.
    - `argon2-cffi==25.1.0`, `argon2-cffi-bindings==26.1.0`, `asyncpg==0.32.0`, `bcrypt==5.0.0`, `cffi==2.1.1`, `ecdsa==0.19.2`, `pyasn1==0.6.5`, `pycparser==3.11`, `python-jose==3.5.0`, `rsa==4.9.1`.
    - `certifi==2026.10.23`, `h11==0.16.0`, `httpcore==1.0.9`, `httpx==0.28.1`, `idna==3.20`, `python-multipart==0.0.32`, `PyYAML==6.0.3`, `six==1.17.0`, `opentelemetry-api==1.45.1`, `tzdata==2026.6`.
  - Dev chốt sau verify lần 1 (10/11/2026): `contracts.test.js` là đặc tả, sửa helper cho khớp đúng chuỗi, không sửa test contract; đồng bộ riêng CHECK `thao_tac` trong ORM theo `init.sql` bằng cách thêm `dang_nhap`. Đã hoàn tất cả hai, không ALTER DB.
  - Kết quả frontend chạy lại sau verify lần 1: `npm.cmd test` **46/46** (gồm 17 test contract giữ nguyên và 15 test bổ sung trong `audit-format.test.js`, không lặp các ca contract); `npm.cmd run lint` và `npm.cmd run build` đều đạt. Đã xóa `auditText.js` và test tên cũ. `backend/.venv/Scripts/python.exe -m ruff check backend/app/modules/audit/models.py` và `-m ruff format --check backend/app/modules/audit/models.py` đạt; đối chiếu danh sách CHECK ORM với SQL khớp chính xác.
  - Playwright — kết quả cuối, đã xác nhận ở verify lần 3: chạy cả `admin-ui.spec.js` với `playwright.config.js` gốc **3 lượt liên tiếp, mỗi lượt 11/11 đạt**, không retry/skip. Nguyên nhân lỗi cache là cwd có drive viết thường `d:\...`: ứng dụng nạp `query-client.js` qua `/@fs/D:/Workspace/xbike-mrp-system/frontend/src/lib/query-client.js`, còn test dùng `/src/lib/query-client.js`, tạo **2 URL module → 2 QueryClient**; không phải fixture rò state hay logic lưu hồ sơ. Sửa `frontend/vite.config.js` đặt `root = realpathSync.native(fileURLToPath(new URL(".", import.meta.url)))`; trace sau sửa chỉ còn một URL module. **Dev chốt giữ thay đổi này ngày 10/11/2026 (ngoài plan ban đầu).** Giữ nguyên `UsersPage.jsx`, `playwright.config.js`, assertion và số test. Giới hạn: Playwright trên Windows có thể treo ở bước dừng Vite sau khi đã có đủ kết quả; reporter đã ghi đủ trạng thái từng test trước khi ngắt tiến trình, không báo CLI exit 0. `npm.cmd test` **46/46**, lint/build đạt, cả ba lệnh exit 0. Ảnh ADM-01 được chụp tại 1440×900 và 1672×941, không lộ giá trị hồ sơ.
  - Căn cứ đóng mục: Backend đã bổ sung dữ liệu/quyền đọc D-HD-01, frontend tích hợp và kiểm thử ADM-01; không đồng nghĩa toàn bộ suite của repo xanh hoặc đã nghiệm thu E2E DB thật.
  - Giới hạn: Không kiểm tra/ghi DB ứng dụng. DB có CHECK `dang_nhap` không cần đổi schema; `init.sql` đã có từ commit `2ef564c`, tác vụ bổ sung COMMENT SQL và đồng bộ CHECK ở source ORM. Volume tạo trước commit này có thể chưa có CHECK và đăng nhập sẽ trả 500; không tự ALTER/reset/seed. Không có Mermaid CLI/package trong môi trường: đã đối chiếu sequence với router/service/repository/dependency, chưa render/parse bằng Mermaid. `/admin/lich-su` còn nội dung giới thiệu cũ về audit rút gọn; giữ nguyên vì ngoài phạm vi sửa trang này.
  - Câu hỏi còn mở trong FE-MISS-004: Không còn; hai câu hỏi ở verify lần 1 đã được dev chốt và xử lý.

Bảng ánh xạ mã nghiệp vụ đã đối chiếu tại nơi ghi audit (Bước 3):

| Loại đối tượng | Trường dùng trong snapshot | Nguồn đối chiếu |
| --- | --- | --- |
| `nhan_vien` | `ma_nhan_vien` | `nhan_vien/service.py` `_audit`, `schemas.py` `NhanVienRead` |
| `vai_tro` | `ten_vai_tro` (tên, không phải mã) | D-VT-01 không có endpoint ghi; fallback snapshot lịch sử theo plan |
| `mat_hang` | `ma_mat_hang` | `mat_hang/service.py` `_audit`, `schemas.py` |
| `nha_cung_cap` | `ma_ncc` | `nha_cung_cap/service.py` `create`, repository `flush_created_record` và model |
| `cong_thuc` | Không có mã → `#doi_tuong_id` | `bom/service.py` `_audit`, `BomRead` chỉ có ID/version |
| `phieu_nhap` | `ma_phieu_nhap` | `phieu_nhap/service.py` `_audit_change`/tạo phiếu, `PhieuNhapRead` |
| `phieu_xuat` | `ma_phieu_xuat` | `phieu_xuat/service.py` `_audit`/duyệt, `PhieuXuatRead` và record values |
| `yeu_cau_san_xuat` | `ma_yeu_cau_san_xuat` | `san_xuat/service/yeu_cau_san_xuat.py` `_audit`, `YeuCauRead`; audit từ `lenh_san_xuat.py` |
| `lenh_san_xuat` | `ma_lenh_san_xuat` | `san_xuat/service/lenh_san_xuat.py` `_audit`, `LenhRead`; audit hoàn tất từ `chung_tu_hoan_thanh_sx.py` |
| `chung_tu_hoan_thanh_san_xuat` | `ma_phieu` | `san_xuat/service/chung_tu_hoan_thanh_sx.py` `_audit`, `HoanThanhRead` kế thừa `ChungTuRead` |
| `phieu_dieu_chinh_kho` | `ma_phieu` | `dieu_chinh_kho/service.py` `_audit`, `PhieuDieuChinhRead` |
| `ticket_loi_dieu_chinh` | `ma_ticket` | `dieu_chinh_kho/service.py` ghi audit ticket, `TicketRead` |

Đối tượng kho giữ văn phong contract: `<loại> <mã hoặc #id> · <lý do>` (bỏ phần lý do khi không có), ví dụ `phiếu nhập #2 · đã kiểm tra`. Với loại nghiệp vụ thiếu mã trong snapshot sau, dùng mã snapshot trước nếu có (bao gồm xóa nháp sản xuất ghi snapshot sau `{}`); cuối cùng `#doi_tuong_id`. Không hiển thị trường snapshot khác.

- [x] FE-MISS-005 — Đặt lại mật khẩu nhân viên dành cho Quản trị viên
  - Màn hình / mã yêu cầu / ảnh thiết kế: ADM-03 Chi tiết tài khoản / Chế độ chỉnh sửa (`DET-Q02`).
  - Thành phần hoặc thao tác bị ảnh hưởng: Hàng “Mật khẩu” ở trang chi tiết tài khoản khi ở chế độ xem và chế độ chỉnh sửa trực tiếp.
  - Thiết kế yêu cầu: Quyết định mới 10/11/2026 cập nhật giới hạn chỉ đọc trước đây: chế độ xem giữ `••••••••`; chế độ sửa có một ô “Để trống nếu không đổi” và nút hiện/ẩn, lưu chung nút `Lưu` và popup `Xác nhận thay đổi`, không ô lý do.
  - API hiện đáp ứng: Đã bổ sung `POST /api/v1/nhan_vien/{id}/dat_lai_mat_khau`, chỉ admin, body `mat_khau_moi` 8–1024 ký tự không trim, không trường thừa/query; bắt buộc `If-Match`; response `NhanVienDetailResponse` + ETag. Không sửa schema DB, PATCH hoặc `/auth/doi_mat_khau`.
  - Bằng chứng: `nhan_vien/{router,schemas,service}.py`, `frontend/src/features/auth/UsersPage.jsx`, `frontend/src/app/App.css`, test browser `admin-ui.spec.js`/`api-fixture.js`, quyết định D-MK-01 và `docs/sequence/nhan_vien.md`. Repository/port `set_password_hash` đã có, tái sử dụng nguyên trạng. Helper `dashboard/auditFormat.js` giữ nguyên, dùng đúng `du_lieu_sau={"da_dat_lai_mat_khau": true}`.
  - Phản hồi dev 10/11/2026: Bổ sung API + ô nhập inline; áp dụng mọi tài khoản gồm chính admin và tài khoản bị khóa; không lý do. Admin tự reset KHÔNG đăng xuất: FE gọi `login()` với mật khẩu mới ngay sau reset trước mọi invalidate/refetch/cập nhật cache. Chỉ login lỗi mới logout với “Đã đặt lại mật khẩu. Vui lòng đăng nhập lại.”. Đây là bổ sung ngoài SRS_v4/contract v3.1; dev tự cập nhật Drive.
  - Kết quả triển khai: Lưu lần lượt hồ sơ → vai trò → mật khẩu; nối ETag, giữ nháp và không gửi lại bước thành công khi lỗi một phần. Xóa nháp khi vào/thoát sửa, đổi ID, Hủy hoặc lưu xong. Audit cùng transaction, không chứa mật khẩu/hash; token cũ của tài khoản đích bị vô hiệu qua `pwdv`. Tự login có thêm dòng audit “Đăng nhập”, được chấp nhận trong plan.
  - Kiểm thử backend tạm (không DB): tại `backend/`, `.venv/Scripts/python.exe -m pytest tests/test_tam_fe_miss_005.py -q` đạt **25/25** (lượt cuối 4.20s), bao phủ 200 + ETag cho nhân viên/quản lý/bị khóa/chính admin, hash thật và không trim, audit đúng marker, 4cd01/403/404/428/412/422, biên 8/1024, PATCH vẫn từ chối mật khẩu, rollback khi audit lỗi và pwdv cũ bị từ chối. Lượt đầu 24 đạt/25, 1 lỗi trong test do truyền keyword-only theo vị trí; đã sửa test rồi chạy lại đạt 25/25 hai lần. File tạm được xóa sau khi ghi kết quả; giữ nguyên `backend/tests/test_nhan_vien_create_code.py`.
  - Ruff tại `backend/`: `.venv/Scripts/python.exe -m ruff check app/modules/nhan_vien tests/test_tam_fe_miss_005.py` đạt; `.venv/Scripts/python.exe -m ruff format --check app/modules/nhan_vien tests/test_tam_fe_miss_005.py` đạt (8 file). Lượt format-check đầu báo 1 file test tạm cần format; đã chạy ruff format file tạm và kiểm tra lại đạt. Không format lại file của dev ngoài phạm vi.
  - Frontend tại `frontend/`: `npm test` ban đầu bị PowerShell chặn `npm.ps1`; chạy `npm.cmd test` đạt **46/46**, 0 failed; `npm run lint` đạt; `npm run build` đạt. Giữ nguyên `frontend/tests/contracts.test.js`.
  - Playwright: chạy cả file bằng `node node_modules/@playwright/test/cli.js test tests/browser/admin-ui.spec.js --reporter=line`, dùng `playwright.config.js` gốc, **hai lượt liên tiếp**: lượt 1 **18 passed / 0 failed** (3.4m), lượt 2 **18 passed / 0 failed** (1.6m). Cả hai treo bước dừng Vite sau các ca; dừng riêng tiến trình Vite của từng lượt, runner in tổng kết trên và exit 0. Bao phủ reset rỗng/7 ký tự, hiện/ẩn/Hủy, chuỗi PATCH → PUT nếu có → reset với If-Match, retry lỗi một phần, tự reset → login không token cũ → `/auth/me` token mới, và login 500 → logout có thông báo.
  - Ảnh đã mở kiểm tra: `frontend/test-results/adm-03-inline-edit-1670x941.png` (có ô mật khẩu và nút mắt, hàng giữ cùng kiểu/chiều cao so với `doc/ui-admin-screenshots/02-inline-edit.png`); có thêm ảnh 1440×900 và 375×812 trong cùng thư mục.
  - Giới hạn: chưa có PostgreSQL test riêng được xác nhận, nên chưa kiểm chứng tự reset/khóa lặp không deadlock và rollback bằng DB thật; test transaction dùng mock. Playwright dùng API fixture, chưa phải E2E backend + PostgreSQL thật. Sequence đã đối chiếu source, chưa render/parse bằng Mermaid vì không có công cụ sẵn có. Không xóa/seed/reset DB, không chỉnh Drive, không commit/push. Không còn câu hỏi mở trong phạm vi FE-MISS-005.

## UI nhân viên — các mục còn mở (11/11/2026)

Theo quyết định ngày 11/11/2026 của dev, giao diện nhân viên chuyển sang chuẩn hóa theo `XBIKE_Employee_Portal_Preview (1).html` (lưu tại `doc/ui-nhan-vien-preview/employee-portal-preview.html`). Dưới đây là các phần giao diện prototype preview có yêu cầu nhưng API hiện tại chưa hỗ trợ hoặc khác biệt về phân quyền backend, được ghi nhận theo đúng FRONTEND_RULES.md:

- [ ] FE-MISS-006 — Khác biệt preview: Trường sản phẩm lỗi (`badQty`) và ghi chú sản xuất (`note`) trong chứng từ hoàn thành
  - Màn hình / mã yêu cầu / ảnh thiết kế: Chứng từ hoàn thành (`/nv/hoan-thanh`) — form tạo chứng từ (`documentModal`) trong `XBIKE_Employee_Portal_Preview (1).html`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Ô nhập `Sản phẩm lỗi` (`docBad`) và textarea `Ghi chú sản xuất` (`docNote`).
  - Thiết kế yêu cầu: Nhân viên ghi nhận cả số lượng đạt (`qty`), số lượng lỗi (`badQty`), và ghi chú ca làm việc khi tạo chứng từ hoàn thành.
  - API hiện đáp ứng / còn thiếu: `HoanThanhCreate` trong `backend/app/modules/san_xuat/schemas.py` hiện chỉ nhận `lenh_san_xuat_id`, `so_luong_hoan_thanh`, `finish_time` với `extra="forbid"`. Backend chưa có cột/trường cho số lượng lỗi và ghi chú chứng từ.
  - Bằng chứng: `backend/app/modules/san_xuat/schemas.py` dòng 234–244; router `/chung_tu_hoan_thanh_sx`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Quyết định ngày 12/11/2026 của dev là giữ nguyên nghiệp vụ/quyền/API hiện tại, ghi riêng khác biệt preview để chờ duyệt. Theo FRONTEND_RULES, không hiển thị các ô nhập không được hỗ trợ rồi âm thầm bỏ qua (`extra="forbid"` gây lỗi 422 nếu gửi). Do đó form tạo chứng từ chỉ nhận các trường được API hỗ trợ (`so_luong_hoan_thanh`, `finish_time`). Khác biệt về trường `badQty` và `note` được ghi nhận tại đây chờ dev quyết định mở rộng backend.
  - Câu hỏi / quyết định cần dev xác nhận: Backend có bổ sung hai trường `so_luong_loi` và `ghi_chu` vào schema `HoanThanhCreate`/database hay giữ ở mức ghi nhận tạm thời trên giao diện.
  - Phản hồi của dev: Ngày 12/11/2026 dev đã quyết định giữ nguyên nghiệp vụ/quyền/API hiện tại; ghi riêng các khác biệt preview để chờ duyệt.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Giữ `[ ]` chờ dev quyết định.

- [ ] FE-MISS-007 — Khác biệt preview: Quyền tạo phiếu xuất thành phẩm (`create-issue`) của Nhân viên
  - Màn hình / mã yêu cầu / ảnh thiết kế: Tổng quan (`/nv`), Yêu cầu sản xuất (`/nv/yeu-cau`), Tra cứu phiếu xuất (`/nv/phieu-xuat`) — nút `+ Tạo phiếu xuất thành phẩm` và modal `issueModal` trong `XBIKE_Employee_Portal_Preview (1).html`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Nút mở modal và form gửi phiếu xuất thành phẩm ở trạng thái chờ duyệt.
  - Thiết kế yêu cầu: Nhân viên được phép lập phiếu xuất thành phẩm cho yêu cầu đã đủ điều kiện (đủ tồn khả dụng hoặc đã duyệt hoàn thành) để gửi quản lý phê duyệt.
  - API hiện đáp ứng / còn thiếu: Trong `backend/app/modules/phieu_xuat/router.py`, các thao tác ghi phiếu xuất (`POST /api/v1/phieu_xuat`) sử dụng `WriteActor = Annotated[dict, Depends(write_actor)]` giới hạn quyền `quan_ly`. Nếu nhân viên gọi trực tiếp sẽ nhận 403 Forbidden.
  - Bằng chứng: `backend/app/modules/phieu_xuat/router.py` dòng 47–49; `frontend/src/features/material-issuing/MaterialIssuingPage.jsx`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Quyết định ngày 12/11/2026 của dev là giữ nguyên quyền/API hiện tại. Backend hiện chỉ cấp quyền ghi phiếu xuất cho vai trò `quan_ly`. Không tự tiện dựng nút tạo phiếu xuất khả dụng rồi gửi bị 403, cũng không tự ý chuyển thành yêu cầu khác hay giả lập lưu client. Nhân viên chỉ tra cứu phiếu xuất được phân công (`/nv/phieu-xuat`). Khác biệt về quyền lập phiếu xuất thành phẩm được ghi nhận tại đây chờ dev duyệt mở quyền backend.
  - Câu hỏi / quyết định cần dev xác nhận: Có mở quyền tạo phiếu xuất nháp / chờ duyệt cho nhân viên (`WriteActor` chấp nhận `nhan_vien` cho phiếu xuất thành phẩm) hay giữ nguyên quyền lập phiếu chỉ dành cho `quan_ly`.
  - Phản hồi của dev: Ngày 12/11/2026 dev đã quyết định giữ nguyên quyền và API hiện tại; ghi riêng khác biệt preview để chờ duyệt.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Giữ `[ ]` chờ dev quyết định.

- [ ] FE-MISS-008 — Khác biệt preview: Mức cảnh báo tồn kho tối thiểu (`min`) và đánh dấu trạng thái tồn thấp/thiếu
  - Màn hình / mã yêu cầu / ảnh thiết kế: Tra cứu tồn kho (`/nv/ton-kho`) trong `XBIKE_Employee_Portal_Preview (1).html`.
  - Thành phần hoặc thao tác bị ảnh hưởng: Cột `Tình trạng` hiển thị tag `Đủ tồn tối thiểu` hoặc `Thấp / thiếu` dựa trên so sánh `available < min`.
  - Thiết kế yêu cầu: Hiển thị mức tồn tối thiểu (`min`) và cảnh báo mặt hàng thiếu tồn.
  - API hiện đáp ứng / còn thiếu: Schema `MatHangRead` trong `backend/app/modules/mat_hang/schemas.py` có `so_luong_ton`, `don_vi_tinh`, `don_gia`, `is_active` nhưng chưa có trường `ton_kho_toi_thieu` hoặc `min_stock`.
  - Bằng chứng: `backend/app/modules/mat_hang/schemas.py` dòng 23–38; bảng `"MatHang"` trong `infra/postgres/init.sql`.
  - Ảnh hưởng và phần vẫn tiếp tục làm được: Quyết định ngày 12/11/2026 của dev là giữ nguyên API hiện tại. Backend `MatHangRead` chỉ trả `so_luong_ton`, không có `min_stock` hay `ton_kho_toi_thieu` và không phân tách số dư khả dụng riêng. Không tự đặt ngưỡng tùy tiện hay gán nhãn khả dụng giả. Bảng tra cứu tồn kho hiển thị đúng `so_luong_ton` thực tế từ API.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung trường `ton_kho_toi_thieu` vào bảng `"MatHang"` và `MatHangRead` không, hay áp dụng ngưỡng cảnh báo mặc định ở frontend.
  - Phản hồi của dev: Ngày 12/11/2026 dev đã quyết định giữ nguyên API hiện tại; ghi riêng khác biệt preview để chờ duyệt.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Giữ `[ ]` chờ dev quyết định.

- [ ] FE-MISS-009 — Khác biệt preview trên trang Lệnh sản xuất: hạn hoàn thành, tìm theo sản phẩm/SKU và nhóm lọc tổng hợp
  - Màn hình / mã yêu cầu / ảnh thiết kế: `/nv/lenh-sx`, UI-NV-05, `doc/ui-nhan-vien-preview/orders-1440.png`.
  - Thành phần bị ảnh hưởng: Cột và mục chi tiết `Hạn hoàn thành`; ô tìm theo mã yêu cầu/tên thành phẩm/SKU; thẻ lọc `Chờ cấp vật tư` và `Chờ duyệt chứng từ`.
  - Thiết kế yêu cầu: Xem ngày hạn, tìm đa trường và đếm/lọc lệnh theo hai nhóm tổng hợp của preview.
  - API hiện đáp ứng / còn thiếu: `LenhRead` chỉ có `created_at`, `started_at`, `completed_at`, không có hạn hoàn thành; `q` của danh sách lệnh chỉ lọc `ma_lenh_san_xuat`; `LenhStatus` chỉ có `nhap`, `da_gui`, `dang_thuc_hien`, `hoan_thanh`, `da_huy`.
  - Bằng chứng: `backend/app/modules/san_xuat/schemas.py` dòng 15, 138–156; `backend/app/modules/san_xuat/repository/lenh_san_xuat.py` dòng 94–95.
  - Ảnh hưởng và phần tiếp tục làm được: Theo quyết định giữ nghiệp vụ/quyền/API hiện tại, UI hiển thị `started_at`, tìm theo mã lệnh và dùng bốn thẻ đếm/lọc `Tất cả`, `Đã giao`, `Đang thực hiện`, `Hoàn thành` qua `meta.total`; không coi một trang phân trang là toàn bộ lệnh để tự gán nhóm tổng hợp.
  - Câu hỏi / quyết định cần dev xác nhận: Có mở rộng hợp đồng API cho hạn hoàn thành, tìm đa trường và bộ lọc/aggregate theo trạng thái tổng hợp của preview không.
  - Phản hồi của dev: Ngày 12/11/2026 dev chọn giữ nghiệp vụ/quyền/API hiện tại và ghi riêng khác biệt preview chờ duyệt.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Giữ `[ ]` tới khi dev quyết định phần khác biệt.

- [ ] FE-MISS-010 — Khác biệt preview trong chi tiết Yêu cầu sản xuất: ghi chú xử lý và vật tư BOM tổng hợp
  - Màn hình / mã yêu cầu / ảnh thiết kế: `/nv/yeu-cau/:id`, UI-NV-06, `doc/ui-nhan-vien-preview/requests-1440.png` và modal chi tiết trong HTML preview.
  - Thành phần bị ảnh hưởng: Khối ghi chú xử lý và bảng vật tư/BOM ở cấp yêu cầu.
  - Thiết kế yêu cầu: Xem ghi chú và tổng nhu cầu vật tư liên quan đến toàn bộ yêu cầu ngay trong modal.
  - API hiện đáp ứng / còn thiếu: `YeuCauRead` không có ghi chú hay danh sách vật tư; `KeHoachRead` trả danh sách lệnh đã chốt nhưng không trả bảng vật tư tổng hợp. API `/lenh_san_xuat/{id}/vat_tu` hỗ trợ xem vật tư theo từng lệnh được phân công.
  - Bằng chứng: `backend/app/modules/san_xuat/schemas.py` dòng 79–93, 172–175 và router lệnh `/{id}/vat_tu`.
  - Ảnh hưởng và phần tiếp tục làm được: UI hiển thị trường yêu cầu và cây lệnh có thật; vật tư xem trong chi tiết lệnh khi nhân viên có quyền truy cập, không suy diễn ghi chú hoặc gộp số liệu từ các lệnh ngoài phạm vi được giao.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung ghi chú và phép đọc vật tư/BOM tổng hợp cấp yêu cầu cùng quy tắc phân quyền tương ứng không.
  - Phản hồi của dev: Ngày 12/11/2026 dev chọn giữ nghiệp vụ/quyền/API hiện tại và ghi riêng khác biệt preview chờ duyệt.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Giữ `[ ]` tới khi dev quyết định phần khác biệt.

- [ ] FE-MISS-011 — Khác biệt preview về các nhóm tổng hợp mức sẵn sàng của yêu cầu sản xuất
  - Màn hình / mã yêu cầu / ảnh thiết kế: `/nv` và `/nv/yeu-cau`, UI-NV-04/06, `doc/ui-nhan-vien-preview/overview-1440.png` và `requests-1440.png`.
  - Thành phần bị ảnh hưởng: Thẻ đếm `Sẵn sàng xuất thành phẩm` và các tab `Sẵn sàng xuất`, `Cần sản xuất`, `Chờ duyệt chứng từ` trong preview.
  - Thiết kế yêu cầu: Đếm và lọc yêu cầu theo mức sẵn sàng tổng hợp từ tồn thành phẩm, lệnh liên quan và chứng từ đã duyệt.
  - API hiện đáp ứng / còn thiếu: Danh sách yêu cầu chỉ lọc theo `YeuCauStatus`; `YeuCauRead` không trả cờ hay số đếm tổng hợp sẵn sàng, còn tồn kho mặt hàng là số dư chung và không xác nhận phần tồn đã dành cho từng yêu cầu. Không suy ra nhóm này từ một trang kết quả hoặc từ phép so sánh số dư đơn giản.
  - Bằng chứng: `backend/app/modules/san_xuat/schemas.py` (`YeuCauStatus`, `YeuCauRead`), router/repository danh sách yêu cầu và `backend/app/modules/mat_hang/schemas.py` (`MatHangRead.so_luong_ton`).
  - Ảnh hưởng và phần tiếp tục làm được: UI dùng KPI và bộ lọc theo trạng thái API thực, giữ danh sách yêu cầu và quyền chỉ đọc của nhân viên; không hiển thị nhãn `Sẵn sàng xuất` khi backend chưa xác nhận.
  - Câu hỏi / quyết định cần dev xác nhận: Có bổ sung phép tính và bộ lọc/số đếm tổng hợp mức sẵn sàng theo quyền nhân viên không.
  - Phản hồi của dev: Ngày 12/11/2026 dev chọn giữ nghiệp vụ/quyền/API hiện tại và ghi riêng khác biệt preview chờ duyệt.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Giữ `[ ]` tới khi dev quyết định phần khác biệt.

- [ ] NV-CHECK-001 — Hoàn tất kiểm chứng accessibility (`UI-11`).
  - Còn mở: zoom trình duyệt thực tế 200%, lấy mẫu tương phản đầy đủ các trạng thái và các giới hạn dialog nêu trong đặc tả.
  - Đã có bằng chứng: kiểm tra bàn phím/focus/busy state trong browser fixture; tên mặt hàng dài 167 ký tự xuống dòng và số lượng tồn vẫn hiển thị ở 375px; Astra kiểm tra riêng QuickStock/RecentAudit quản lý tại 375×812 và 1440×812. Viewport thu nhỏ không được coi là bằng chứng zoom trình duyệt thực tế.
  - Căn cứ đóng mục: thực hiện và ghi kết quả các kiểm tra còn mở; chưa tự đánh dấu hoàn tất.
- [ ] NV-CHECK-002 — Kiểm chứng phân quyền hai tài khoản và E2E API/PostgreSQL thật (`AUTH-04`, `CHECK-04`).
  - Ảnh hưởng: chưa xác nhận toàn bộ luồng nhân viên trên backend/database thật, gồm cô lập dữ liệu theo người dùng và transaction.
  - Bằng chứng hiện có: fixture browser redesign + điều hướng đạt 18/18 ở bản hiện tại. Fixture không chứng minh phân quyền hoặc transaction backend. Chưa có môi trường database test riêng được xác nhận để chạy phần này; không dùng database ứng dụng làm nơi thử ghi.
  - Căn cứ đóng mục: kiểm tra trên môi trường test phù hợp, ghi kết quả thực tế và giới hạn; không tự seed/reset hoặc thay đổi database đang có dữ liệu.
- [ ] NV-CHECK-003 — Dev nghiệm thu UI và kết quả triển khai (`UI-13`, `CHECK-05`).
  - Cần dev xem UI/đặc tả và xác nhận nghiệm thu; kết quả worker review không thay cho nghiệm thu của dev.
  - Căn cứ đóng mục: phản hồi nghiệm thu rõ ràng từ dev. Chưa tự accept, commit hoặc push.

Bằng chứng triển khai theo thứ tự thời gian: `test-run-full.log` 122/122 và `test-employee-targeted.log` 10/10 thuộc đợt UI nhân viên trước redesign; `test-employee-redesign-current.log` 18/18 gồm 11 kiểm tra nhân viên và 7 kiểm tra điều hướng ba vai trò ở bản hiện tại. Lint, 46 unit tests và build đạt; sau khi thêm nhãn ngày dashboard, lint, build và browser 18/18 được chạy lại. Ảnh tại `frontend/test-results/` do lượt browser cuối tạo ra; đã mở xem ảnh desktop/mobile, dialog và giao diện quản lý. Những chỉnh sửa của đợt redesign này chỉ thuộc frontend/test/tài liệu; diff `backend/Dockerfile` đã có từ trước và không bị sửa trong đợt này. Không có thay đổi hợp đồng API, schema hoặc bootstrap SQL.

## Mẫu ghi nhận

Mẫu sau chưa phải một vấn đề đã được xác minh:

```markdown
- [ ] FE-MISS-<số> — <Tên phần thiếu>
  - Màn hình / mã yêu cầu / ảnh thiết kế: ...
  - Thành phần hoặc thao tác bị ảnh hưởng: ...
  - Thiết kế yêu cầu: ...
  - API hiện đáp ứng / còn thiếu: ...
  - Bằng chứng: <method + endpoint, trường dữ liệu, đường dẫn source hoặc hợp đồng API; ghi Chưa xác minh nếu chưa đủ căn cứ>
  - Ảnh hưởng và phần vẫn tiếp tục làm được: ...
  - Câu hỏi / quyết định cần dev xác nhận: ...
  - Phản hồi của dev: Chưa có.
  - Kết quả xử lý / kiểm tra / căn cứ đóng mục: Chưa hoàn tất.
```

Giữ `[ ]` khi còn thiếu hoặc đang chờ phản hồi. Chỉ đổi thành `[x]` theo điều kiện bàn giao trong quy tắc frontend và giữ lại nội dung để đối chiếu.
