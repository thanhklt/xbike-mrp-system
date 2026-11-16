# Plan: UC-43 — Xem lịch sử thao tác (đợt frontend, AC-19)

> Lập ngày 15/11/2026. **Dev đã duyệt 15/11/2026 (D1–D5 theo đề xuất; D3 dropdown tên nhân viên; D4 JSON thô, không diff từng field).** Spec: [UC-43](../../specs/use_cases/audit/UC-43.md). Plan đợt backend: [UC-43.md](UC-43.md) (dev duyệt 14/11/2026, backend đã commit `76ebe9a`, frontend hoãn).
> Người thực thi: Codex (`codex exec -s workspace-write`). Claude kiểm chứng theo UC trước khi commit/push.

## Goal

Màn Lịch sử thao tác dùng hai GET đã có (`/api/v1/audit`, `/api/v1/audit/{id}`): QTV và QLK lọc theo người, đối tượng, thao tác, khoảng ngày; đổi trang; mở popup chi tiết thấy trạng thái trước/sau, dữ liệu trước/sau và danh sách thiếu (nếu có). Hai vai trò thấy cùng nội dung (Q02). Không có nút tạo/sửa/xóa/xuất. NV gõ thẳng URL bị chặn. Đóng AC-19, và phần giao diện của AC-1…AC-7, AC-10…AC-13 đang ghi "UI hoãn".

## Context read

- Spec UC-43 (R1–R7, Main 1–6, A1–A3, AC-1…AC-19, Q01–Q06); plan backend UC-43.
- Backend hợp đồng thật: `backend/app/modules/audit/{schemas,router}.py` — `AuditListQuery` (extra=forbid: page, page_size, search, sort_by∈{id,created_at}, sort_order, nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, bo_thao_tac, tu_ngay, den_ngay), `ThaoTac` 20 mã v4, `AuditObject` 8 loại, `AuditDetailResponse {success, data, message}`.
- `specs/entity_model/data_model_v4.md` dòng 496: `du_lieu_sau.danh_sach_thieu = [{mat_hang_id, ma_mat_hang, ten_mat_hang, don_vi_tinh, so_luong_can, so_luong_con_dung, so_luong_thieu}]`.
- FE: `features/reports/AuditPage.jsx`, `routes/index.jsx`, `layouts/{navigation.js,MainLayout.jsx}`, `features/auth/permissions.js`, `features/dashboard/{auditFormat.js,DashboardPage.jsx}`, `lib/api/{contract.js,useResources.js}`, `components/{Collection,RecordPanel,Field,ResourceFields,DataTable,Badge}.jsx`, `lib/format.js`, trang tham chiếu `features/adjustment-tickets/TicketsPage.jsx`.
- Test FE: `tests/{audit-format,navigation,contracts,uc03-account-list}.test.js`.
- Baseline 15/11/2026 trên `identity_access` (HEAD `7fd30f3`): backend **328 pass, 26 skip**, 0 fail; frontend **134 pass**.

## Hiện trạng so với UC-43

| Spec | Hiện trạng FE | Việc cần làm |
|---|---|---|
| Main 1 — QTV/QLK mở lịch sử | Route `/admin/lich-su`, `/kho/lich-su` có. QLK có mục sidebar; **QTV không có lối vào nào** (sidebar QTV cố định 3 mục, Dashboard QTV không có link) | D2 |
| Main 2 — danh sách người, thời điểm, đối tượng, thao tác, lý do | Có cột, nhưng thao tác/đối tượng hiện **mã thô** (`hoan_tat`, `cong_thuc`) | Hiện nhãn tiếng Việt, tái dùng `auditFormat.js` |
| Main 3–4, R5 — lọc đối tượng, người, thao tác, khoảng ngày | Chỉ có sort; Notice "Bộ lọc chuyên sâu… chưa được hỗ trợ" | Thêm 6 filter, bỏ Notice; AND do backend |
| A1 — không có bản ghi | `DataTable` có trạng thái rỗng sẵn | Giữ |
| Main 5–6, R3/R2/R4 — mở chi tiết, trạng thái trước/sau, giá trị trước/sau, danh sách thiếu | Snapshot `<details>` trong dòng, **chỉ QLK**; không gọi GET chi tiết; không có trạng thái trước/sau; không có danh sách thiếu | Popup `RecordPanel` + `useDetail` GET `/audit/{id}` cho cả hai vai trò |
| R6, A3, AC-2 — không sửa/xóa | Không có nút ghi | Giữ: không `useWrite`, không nút sửa/xóa/xuất |
| R7, A2, AC-3 — NV bị chặn | `canAccessPath` + `RoleGate` chặn NV | Giữ; route đổi sang `/:id?` vẫn bị chặn |
| AC-4 — không hiện mật khẩu | Backend đã loại key bí mật | FE hiển thị đúng dữ liệu API trả, không tự dựng thêm |
| AC-07/Q02 — QTV thấy snapshot như QLK | Subtitle "Quản trị viên không được xem snapshot" và cột Dữ liệu chỉ cho QLK | Bỏ phân nhánh theo vai trò |
| AC-12 — sort whitelist | Có option `-id`, thiếu `id` | 4 option `±created_at`, `±id` |
| Thời gian khi popup mở theo URL | Breadcrumb `/admin/lich-su/5` rơi về "Tổng quan" | Thêm nhánh breadcrumb như `/admin/tai-khoan/:id` |

## Quyết định cần dev xác nhận

| Mã | Vấn đề | Đề xuất | Lựa chọn khác |
|---|---|---|---|
| D1 | Nhánh làm việc. PR #11 (identity_access) đã merge; PR #12 còn mở từ `identity_access`. `auditFormat.js` vừa được sửa ở `652057a` (thuộc #12) | Tạo nhánh mới `audit` từ HEAD `identity_access` hiện tại, push `origin audit`; PR riêng vào `main` sau khi xong context audit | Làm tiếp trên `identity_access` (dồn vào PR #12) |
| D2 | QTV không có lối vào màn Lịch sử (Main 1). Test `navigation.test.js` khóa sidebar QTV đúng 3 mục theo quyết định FE trước | Thêm link **"Xem tất cả →"** trỏ `/admin/lich-su` ở card "Hoạt động gần đây" trên Dashboard QTV (cách Dashboard đã làm ở card "Duyệt hoàn thành": `action={<Link …>Xem tất cả →</Link>}`); không đổi sidebar | Thêm mục thứ 4 "Lịch sử thao tác" vào sidebar QTV (phải sửa test navigation) |
| D3 | Lọc "người thực hiện" | **Dropdown chọn nhân viên** ("NV-000005 · Họ tên", option đầu "Tất cả") nạp bằng `useChoices(API.employees)` như ProductionPage/RequestsPage; gửi `nhan_vien_id`. `GET /nhan_vien` đã cho cả QTV và QLK đọc (`NhanVienService.list_employees`; QLK nhận `NhanVienAssignmentRead` có `id, ma_nhan_vien, ho_ten`) nên không đổi backend. Cột "Người thực hiện" trong bảng và popup cũng hiện "mã · họ tên" thay vì `#id` (tên hiện tại, chỉ là nhãn người thao tác — không ghi đè snapshot) | Ô nhập ID nhân viên như plan backend 14/11 (đã ghi nhầm là QLK không đọc được danh sách) |
| D4 | Thứ tự hiển thị trong popup | InfoGrid: Thời gian, Người thực hiện (mã · họ tên, theo D3), Đối tượng (nhãn + #id), Thao tác (nhãn), Trạng thái trước, Trạng thái sau, Lý do (null → "—"); bảng **Danh sách thiếu tại thời điểm thao tác** nếu `du_lieu_sau.danh_sach_thieu` là mảng; sau đó hai khối JSON "Dữ liệu trước" / "Dữ liệu sau" (null → "Không có dữ liệu") | Diff từng field trước/sau (tốn công hơn, spec không đòi) |
| D5 | Nhãn cho mã v4 chưa có trong `auditFormat.js` (copy mới, cần dev đọc) | `dang_nhap` "Đăng nhập", `gui_lai` "Gửi lại", `kiem_tra` "Kiểm tra", `ngung` "Ngừng", `dung_lai` "Dùng lại", `tao_phien_ban` "Tạo phiên bản", `dung_lai_phien_ban` "Dùng lại phiên bản"; đối tượng `cong_thuc` giữ nhãn đang có "BOM" | Tự đặt nhãn khác |

## Khuôn mẫu UI (ui-consistency, đọc 15/11/2026)

AuditPage against **trang danh sách có popup chi tiết** (route `/:id?` + `Collection` + `RecordPanel`, cùng nằm trong `src/features/*`) — từ **TicketsPage** (tham chiếu tự chọn, level 7: trang chỉ đọc-chủ-yếu gần nhất có filter ngày + popup chi tiết + bảng dòng trong popup), 10 thành viên trên 15 file trong `src/features` dùng `Collection`/`RecordPanel`/`useDetail` (loại ProfilePage, MovementsPage, MyDocumentsPage, UsersPage — không theo khuôn Collection+RecordPanel).

- [ ] khung trang — `PageHeader` (title giữ "Lịch sử thao tác", subtitle một câu, **không** phân nhánh theo vai trò) — 10 of 10
- [ ] hàng lọc — qua `Collection filters=[…]`, không form riêng; ngày bằng `dateFilters` dùng chung (`tu_ngay`, `den_ngay`, khớp đúng tên query backend) — the shared piece, 7 trang dùng `dateFilters`
- [ ] filter chọn — `as: "select"`, option đầu `{ value: "", label: "Tất cả" }` như `statusFilter` — the shared piece
- [ ] filter ID — `type: "number", min: 1, step: 1` như "ID phiếu nhập" của TicketsPage — level 3 (tham chiếu)
- [ ] ô tìm kiếm — tắt (`search={false}`): backend chỉ tìm mã thô trong `loai_doi_tuong`/`thao_tac`/`ly_do`, không khớp chữ gợi ý "Tìm mã hoặc tên…"; bộ lọc chuyên biệt thay thế (dev chốt 16/11/2026 khi review PR 13)
- [ ] bảng — `DataTable` qua `Collection`; thời gian bằng `dateTime`; đối tượng/thao tác hiện nhãn qua helper của `auditFormat.js`, không mã thô — the shared piece
- [ ] mở chi tiết — cột link cuối, chữ **"Mở →"** trỏ `${base}/${row.id}` (5 of 10 trang, đa số); nhãn cột đổi thành **"Chi tiết"** thay vì "Thao tác" (9 of 9 dùng "Thao tác") vì ở màn này "Thao tác" là cột nghiệp vụ — lệch có chủ đích, báo ở đây
- [ ] popup — `RecordPanel id query base title="Chi tiết lịch sử thao tác"` + `useDetail(API.audit, id)`; nút Đóng/Tải lại chi tiết có sẵn — the shared piece, 10 of 10
- [ ] thông tin chính — `InfoGrid entries` (null hiện "—" do `InfoGrid`) — the shared piece (TicketsPage)
- [ ] trạng thái trước/sau — `Badge status` (nhãn `STATUS_LABELS`, mã lạ hiện nguyên) — the shared piece
- [ ] danh sách thiếu — `DataTable` cột số `numeric: true` như bảng `chi_tiet` của TicketsPage — level 3
- [ ] JSON trước/sau — `<pre className="audit-json">` hiện có, render text React (không `dangerouslySetInnerHTML`); không thêm CSS/giá trị mới
- [ ] không copy từ TicketsPage: nút "Tạo ticket" vô hiệu, `useWrite`/`confirm`, các nút Nhận xử lý/Giải quyết — màn lịch sử không có thao tác ghi

Ghi chú khuôn mẫu: không thêm màu/khoảng cách/kiểu chữ mới nên không có dòng giá trị riêng. Chi phí: ~22 file dự án mở, ~12 lượt tìm; đọc `finding-patterns/SKILL.md`, `checklist.md`.

## Quy ước comment UC (bắt buộc)

- Hàm/Component tham gia luồng: comment ngay trên định nghĩa
  `// UC-43 Xem lịch sử thao tác — <bước/luồng> (specs/use_cases/audit/UC-43.md)`
- Test: comment ngay trên `test(...)`: `// UC-43 AC-n: <tên AC>` hoặc `// UC-43 A<n>: <tên luồng>`.
- **Chỉ comment đích danh**: `AuditPage` (Main 1–4; R5, A1), `AuditDetail` (Main 5–6; R2, R3, R4, R6), các export của `auditHistory.js` (`AUDIT_ACTION_OPTIONS`, `AUDIT_OBJECT_OPTIONS`, `AUDIT_SORT_OPTIONS`, `auditFilters`, `auditDetailEntries`, `auditShortageRows`) và link "Xem tất cả" ở `RecentAudit` (Main 1, nếu D2 duyệt). Không gắn comment vào hàm phụ trợ khác.

## Backend

Không đổi. Hợp đồng đã đủ cho UI.

## Frontend

| File | Thay đổi |
|---|---|
| `frontend/src/features/reports/auditHistory.js` (mới) | Hàm thuần, không JSX: `AUDIT_ACTION_OPTIONS` (20 mã `ThaoTac`, nhãn từ `auditActionLabel`), `AUDIT_OBJECT_OPTIONS` (8 mã `AuditObject`), `AUDIT_SORT_OPTIONS` (`-created_at` Mới nhất, `created_at` Cũ nhất, `-id` ID giảm dần, `id` ID tăng dần), `auditFilters(employees)` (mảng filter cho `Collection`: Loại đối tượng, ID đối tượng, Người thực hiện — select từ `employees`, Thao tác, …`dateFilters`, Sắp xếp), `auditActorLabel(employees, id)` → "NV-000005 · Họ tên", không tìm thấy → "Nhân viên #id", `auditDetailEntries(record, employees)` → cặp `[nhãn, giá trị]` cho InfoGrid (giá trị nguyên thủy/chuỗi; Badge do JSX bọc), `auditShortageRows(record)` → `record.du_lieu_sau?.danh_sach_thieu` nếu là mảng, ngược lại `[]` |
| `frontend/src/features/dashboard/auditFormat.js` | Export thêm `auditActionLabel(code)` và `auditObjectLabel(code)` từ `ACTION_LABELS`/`OBJECT_LABELS`; bổ sung 7 nhãn mã v4 ở D5. Không đổi đầu ra `formatAuditAction`/`formatAuditDetail` hiện có (test `audit-format.test.js` phải giữ nguyên pass) |
| `frontend/src/features/reports/AuditPage.jsx` | Viết lại theo checklist: `useParams` id, `base` theo vai trò (`/admin/lich-su` hoặc `/kho/lich-su`), `useCollection(API.audit, { sort: "-created_at" }, auditParams)`, `Collection filters={auditFilters}`, `useChoices(API.employees)` cho D3, cột: Thời gian, Người thực hiện (`auditActorLabel`), Đối tượng (nhãn + `<small>#id</small>`), Thao tác (nhãn), Lý do, Chi tiết ("Mở →"). Bỏ Notice "chưa hỗ trợ" và nhánh `manager`. `RecordPanel` + component `AuditDetail` (D4). Không import `useWrite`, không nút ghi/xuất |
| `frontend/src/routes/index.jsx` | `/admin/lich-su` → `/admin/lich-su/:id?`; `/kho/lich-su` → `/kho/lich-su/:id?` |
| `frontend/src/layouts/MainLayout.jsx` | Breadcrumb: `pathname.startsWith("/admin/lich-su/")` → `[{label:"Lịch sử thao tác", to:"/admin/lich-su"}, {label:"Chi tiết lịch sử"}]`, giữ dòng `/admin/lich-su` cũ (theo mẫu `/admin/tai-khoan/`). Phần `/kho` chỉ sửa nếu breadcrumb kho cũng rơi sai khi có `:id` |
| `frontend/src/features/dashboard/DashboardPage.jsx` | (nếu D2 duyệt) card "Hoạt động gần đây" của Dashboard QTV thêm `action={<Link to="/admin/lich-su">Xem tất cả →</Link>}`; không đổi gì khác |
| `frontend/src/lib/api/contract.js` | Không đổi — `auditParams` đã chuyển tiếp mọi field ngoài `q`/`sort` và bỏ giá trị rỗng; test chứng minh |
| `frontend/tests/uc43-audit-history.test.js` (mới) | Xem bảng test ↔ AC |

### Test ↔ AC

Mức test dev đã chọn: `node --test` hàm thuần + đọc source (như `uc03-account-list.test.js`). Không chạy Playwright.

| AC / luồng | Test (`tests/uc43-audit-history.test.js`) | Assert |
|---|---|---|
| AC-1, R4 | `auditShortageRows` | Bản ghi `du_lieu_sau.danh_sach_thieu` 1 dòng `so_luong_thieu: 10` → trả đúng dòng đó; `du_lieu_sau` null hoặc không có mảng → `[]` |
| AC-2, R6, A3 | AuditPage chỉ đọc | Source `AuditPage.jsx` không chứa `useWrite`, `mutateAsync`, `dangerouslySetInnerHTML` và không có `<Button` nào ngoài khung shared (không nút sửa/xóa/xuất); `auditHistory.js` không chứa phương thức ghi |
| AC-3, A2, R7 | NV bị chặn | `canAccessPath("nhan_vien", p)` false với `/admin/lich-su`, `/admin/lich-su/5`, `/kho/lich-su`, `/kho/lich-su/5`; đối chứng QTV → `/admin/lich-su/5` true, QLK → `/kho/lich-su/5` true; `routes/index.jsx` có đúng hai path `:id?` |
| AC-4 | Không tự dựng mật khẩu | `auditDetailEntries` không sinh nhãn/giá trị chứa "mật khẩu"/"password" với bản ghi `doi_mat_khau` đã redaction; nhãn hành động là "Đổi mật khẩu" |
| AC-5 | Lọc theo công thức | `AUDIT_OBJECT_OPTIONS` có `cong_thuc` nhãn "BOM"; `AUDIT_ACTION_OPTIONS` có `tao_phien_ban` nhãn "Tạo phiên bản"; `auditParams({loai_doi_tuong:"cong_thuc", …})` chuyển tiếp đúng |
| AC-6, AC-10, R5 (D3) | Người thực hiện theo tên | `auditFilters(employees)` có select `nhan_vien_id` với option "Tất cả" + mỗi nhân viên `{value: id, label: "mã · họ tên"}`; `auditActorLabel` có/không tìm thấy nhân viên |
| AC-6, AC-10, R5 | Lọc kết hợp | `auditFilters` có đủ name `loai_doi_tuong, doi_tuong_id, nhan_vien_id, thao_tac, tu_ngay, den_ngay`; `auditParams` với người + khoảng ngày → query đúng tên backend, bỏ ô rỗng, giữ `page` |
| AC-07, Q02 | Hai vai trò cùng nội dung | Source `AuditPage.jsx` không còn phân nhánh `ma_vai_tro === "quan_ly"` cho cột/khối dữ liệu; `auditDetailEntries` không nhận vai trò |
| AC-12 | Sort whitelist | 4 giá trị `AUDIT_SORT_OPTIONS` ánh xạ qua `auditParams` ra `sort_by` ∈ Literal `sort_by` đọc từ `backend/app/modules/audit/schemas.py` |
| AC-13, A8 | Null giữ nguyên | Bản ghi `trang_thai_truoc/sau`, `ly_do`, `du_lieu_*` null → `auditDetailEntries` trả `null` cho các ô đó (InfoGrid hiện "—"), không suy ra giá trị |
| AC-19, R1–R2 | Mã hợp đồng khớp backend | Giá trị `AUDIT_ACTION_OPTIONS` == `ThaoTac`, `AUDIT_OBJECT_OPTIONS` == `AuditObject` đọc từ `schemas.py` (thứ tự tùy ý); mọi mã có nhãn tiếng Việt (không fallback mã thô) |
| AC-19 (Main 1, D2) | Lối vào QTV | Source `DashboardPage.jsx` có `to="/admin/lich-su"` (nếu D2 duyệt) |

Không sửa test cũ. `audit-format.test.js`, `navigation.test.js`, `contracts.test.js` phải giữ pass.

## Tài liệu

- Không đổi endpoint → không sửa `docs/sequence/audit.md`.
- Sau khi đạt: cập nhật dòng AC-19 và cột "UI hoãn" trong spec UC-43 mục 8, dòng T07 trong `docs/plans/UC-43.md`.

## Ràng buộc cho Codex

- Đọc `AGENTS.md` trước. Chỉ sửa file trong bảng Frontend. Không đụng backend, DB, Docker, seed, dependency, lockfile, CSS toàn cục, `Collection`/`RecordPanel`/`Field`/`DataTable` dùng chung.
- Không commit, không push. Không sửa test cũ, không sửa browser test.
- Chạy đủ lệnh kiểm chứng, báo file đã sửa, kết quả thực tế từng lệnh, điểm lệch plan. Không sửa mục "Kết quả".

## Kiểm chứng

```bash
cd frontend && node --test tests/uc43-audit-history.test.js
cd frontend && npm test
cd frontend && npx eslint src/features/reports src/features/dashboard/auditFormat.js src/features/dashboard/DashboardPage.jsx src/routes/index.jsx src/layouts/MainLayout.jsx tests/uc43-audit-history.test.js
cd frontend && npm run build
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider
```

Đạt khi: test UC-43 pass 100%; `npm test` ≥ 134 cũ pass + test mới, 0 fail; backend vẫn 328 pass/26 skip; eslint sạch trên file đã sửa; build thành công.

Commit dự kiến: `feat(UC-43): màn lịch sử thao tác có bộ lọc và chi tiết bản ghi cho QTV, QLK`

## Ngoài phạm vi

- Backend, producer audit của UC khác (E2E sinh audit AC-1/AC-5), xuất file.
- Playwright: `workflows.spec.js` "admin sees no … snapshot" mang tên cũ trái Q02 (assert vẫn đúng vì snapshot chuyển vào popup) — không sửa, không chạy.
- Diff từng field (D4). Đổi quyền API nhân viên (không cần, D3).

## Kết quả

Thực thi 15/11/2026 trên nhánh `audit` tách từ `identity_access` @ `7fd30f3`. Codex làm phần chính; Claude kiểm chứng và sửa thêm như ghi bên dưới.

**File đã sửa/tạo (frontend):** `src/features/reports/auditHistory.js` (mới), `src/features/reports/AuditPage.jsx`, `src/features/dashboard/auditFormat.js`, `src/features/dashboard/DashboardPage.jsx` (chỉ link D2), `src/routes/index.jsx`, `src/layouts/MainLayout.jsx`, `src/app/App.css` (lệch plan, xem dưới), `tests/uc43-audit-history.test.js` (mới, 16 test).

| Lệnh | Kết quả |
|---|---|
| `node --test tests/uc43-audit-history.test.js` | 16 pass, 0 fail |
| `npm test` | 155 pass, 0 fail (139 test cũ trên `7fd30f3` + 16 mới) |
| `npx eslint …` (file đã sửa) | 0 lỗi |
| `npm run build` | **Lỗi có sẵn, không do UC-43:** `Sidebar.jsx` import `doc/ui-spec-admin/tong_quan.png`, file này không có trong git |
| `pytest` toàn backend | 328 pass, 26 skip, 0 fail (không đổi backend) |

| AC | Test | Kết quả |
|---|---|---|
| AC-1, R4 | `shortages preserve the stored row…`, `shortage table uses snapshot codes…` | Pass |
| AC-2, R6, A3 | `audit presentation has no write or export controls…` | Pass |
| AC-3, A2, R7 | `employees cannot open either audit list or detail…` | Pass |
| AC-4 | `password change details use redacted evidence…` | Pass |
| AC-5 | `BOM version filtering sends the approved object and action codes` | Pass |
| AC-6, AC-10 (D3) | `actor select contains all employees…`, `all six filters use backend names…`, `combined filters preserve pagination…` | Pass |
| AC-07 | `both roles use the same data columns and detail component` | Pass |
| AC-12 | `all four sort choices map exactly to the backend sort whitelist` | Pass |
| AC-13, A8 | `nullable evidence stays null…` | Pass |
| AC-19 | `action and object options exactly match backend literals…`, `detail entries keep the approved order…`, `details load by route ID in RecordPanel…`, `administrator dashboard activity card links to the audit history` | Pass |

**Claude sửa thêm khi kiểm chứng:**
- Nhánh `audit` ban đầu tình cờ tách từ `aab3a0d`: lúc tạo nhánh, một session khác (reporting) đang dùng chung thư mục này. Đã đưa nhánh về `7fd30f3` theo D1 và gộp lại `auditFormat.js` với `ACCOUNT_ACTIONS_V4` của `652057a`.
- `auditActionLabel` dùng lại `ACCOUNT_ACTIONS_V4` thay vì khai báo bản sao.
- D2: Codex dừng vì `RecentAudit` là card của QLK. Claude thêm link "Xem tất cả →" vào cuối card "Hoạt động gần đây" của `AdminDashboard` bằng các class có sẵn `.actions.actions-end`, và thêm test cho link này.
- Cột mặt hàng trong bảng danh sách thiếu chịu được trường hợp snapshot thiếu `ma_mat_hang`.
- Kiểm tra ui-consistency do agent riêng làm. Agent hiệu chuẩn tìm ra chỗ cài sẵn (khung thông tin tự viết thay cho `InfoGrid`). Agent kiểm tra trang thật báo các điểm sau, đã sửa: (1) ở giao diện QTV tối, khối `.audit-json` nền sáng còn chữ sáng → thêm rule `html[data-admin-theme="true"] dialog .audit-json` dùng cặp màu ô nhập sẵn có của dialog quản trị (**lệch plan "không thêm CSS"**, cần để QTV đọc được); (2) dòng "Không có dữ liệu" dùng class `.empty-state`, giờ xử lý cả `undefined`; (3) bỏ `caption` trùng với tiêu đề h3 của bảng danh sách thiếu.

**Sửa sau review PR 13 (16/11/2026, dev duyệt):**
- Tắt ô tìm kiếm tự do (`search={false}`), lý do ở mục bộ lọc phía trên.
- Lỗi tải danh sách nhân viên hiện `Notice tone="warning"` kèm nút "Tải lại" (gọi `refetch`, bố cục như `QueryState`) thay vì lặng lẽ chỉ còn "Tất cả" và "Nhân viên #id". Test AC-2 cho phép đúng một `<Button>` này.
- "Từ ngày" sau "Đến ngày" bị chặn ngay trên form: `Collection` nhận prop tùy chọn `validate`, trang lịch sử truyền `dateRangeError`; các trang khác không đổi hành vi.
- `/admin/lich-su/moi`, `/kho/lich-su/moi` chuyển về danh sách thay vì mở popup trống.
- `dateFilters` chuyển sang `components/filterFields.js` (JS thuần), `ResourceFields.jsx` re-export; bỏ bản sao trong `auditHistory.js` và test đối chiếu chuỗi.
- Nhãn "mã · họ tên" dùng chung `employeeLabel` (`lib/format.js`) cho `EmployeeSelect` và trang lịch sử; nhãn người thực hiện tra bằng `Map` dựng một lần (`auditActorLookup`), bỏ `find` lồng trong `map`.
- `auditDetailEntries` gắn kiểu `"status"` cho hai mục trạng thái; `Badge` chọn theo kiểu, không so chữ nhãn.
- `auditShortageRows` trả `null` khi bản ghi không lưu danh sách thiếu (mảng, kể cả rỗng, khi có) và gắn sẵn `id`; trang chỉ gọi một lần.
- Agent kiểm tra ui-consistency (đọc code, đối chiếu TicketsPage, QueryState, App.css) báo và đã sửa: thông báo lỗi bộ lọc dính sát bảng → thêm `.filters + .notice { margin-bottom: 20px }`; bỏ ngoặc kép cong (dự án không dùng); câu chữ theo mẫu "Không thể tải…". Chưa làm: 7 trang khác dùng `dateFilters` chưa truyền `validate` (ngoài phạm vi UC-43).
- Không sửa: nhãn thao tác lệch Tổng quan với bản ghi v3 `sua` (dev quyết định bỏ qua, backend hiện ghi mã riêng `doi_mat_khau`/`mo_khoa`).
- `node --test tests/uc43-audit-history.test.js` 20 pass; `npm test` 159 pass; eslint sạch trên file đã sửa; `npm run build` thành công trên máy local.

**Giới hạn còn lại:**
- Chưa render trình duyệt, nên chưa kiểm tra bằng mắt kích thước, cuộn và độ tương phản thật.
- Nhãn trạng thái v4 (vd. `cho_bo_sung_linh_kien`) chưa có trong `STATUS_LABELS` dùng chung, `Badge` sẽ hiện mã thô.
- Trên Dashboard QTV, cột tương ứng tên "Hành động", còn ở màn Lịch sử tên "Thao tác" (có từ trước).
- Link "Xem tất cả" nằm ở cuối card chứ không ở tiêu đề card như hai dashboard kia, vì `admin-card-title` không có chỗ cho nút hành động.
- Browser test `workflows.spec.js` mang tên cũ trái Q02, chưa sửa và chưa chạy.
