# Plan: Sửa các phát hiện review PR 10 (catalog/BOM v4)

> Dev đã duyệt 16/11/2026: đồng ý D1, D2, D3, D5 theo đề xuất. D4 đổi thành **chỉ sửa BE, không sửa FE** (không có Phase 2 FE trong phạm vi này).
>
> Cập nhật 16/11/2026: `origin/main` nhận PR 9 (BOM) và PR 8 (phiếu nhập). Dev chốt **theo bản main, bỏ D3**: trạng thái lệch được tự đồng bộ theo UC-12 R3. Xem mục "Merge origin/main lần 2" ở phần Kết quả.

## Goal

Đưa PR [thanhklt/xbike-mrp-system#10](https://github.com/thanhklt/xbike-mrp-system/pull/10)
(`feature/catalog`, UC-09→14, UC-44, UC-15→19) về trạng thái merge được vào `main`:

- hết xung đột với `main`;
- sửa các lỗi backend mà review đã phát hiện;
- không phá test hiện có của `main` (production UC-23→33).

Phần frontend (MaterialsPage, BOMPage) **không thuộc plan này**: dev chốt chỉ sửa BE (D4).

## Context read

- Diff `main...pr-10`. Thử merge (`git merge-tree main pr-10`) thì có 4 file xung đột.
- `infra/postgres/init.sql` trên `main` đã là v4 (`GiuHang`, `NhuCauLinhKien`, `Bom.kich_hoat_gan_nhat_at`, trigger mã `MH-`/`NCC-`) và khớp ORM của PR.
- Spec: `specs/use_cases/catalog/UC-11.md` (R1, AC-1→3), `specs/use_cases/bom/UC-17.md` (R3), UC-18 AC-6 (kich_hoat bắt buộc body `{}`, là chủ đích).
- `backend/tests/test_uc23_lap_gui_yeu_cau_san_xuat.py` trên `main` khởi tạo `MatHangRead` thiếu `so_luong_dang_giu`/`so_luong_con_dung`. Sau merge test này sẽ lỗi.

## Bảng phát hiện → việc cần làm

| # | Phát hiện | Việc làm trong plan |
|---|---|---|
| F1 | Xung đột merge; model bị khai báo trùng cột | Bước 0 (Claude): merge `main` và giải xung đột theo bảng bên dưới |
| F2 | API mặt hàng làm vỡ MaterialsPage | Không sửa (D4: chỉ BE) |
| F3 | API BOM làm vỡ BOMPage | Không sửa (D4: chỉ BE) |
| F4 | `has_bom` tính cả `Bom` của chính thành phẩm, nên thành phẩm không đổi được đơn vị tính hay SKU | Sửa SQL `get_references` (D2) |
| F5 | Ngừng/dùng lại mặt hàng báo thành công nhưng không làm gì khi trạng thái mặt hàng và công thức lệch nhau | Trả 409 (D3) |
| F6 | Mỗi instance tạo một `ContextVar` mới | Đổi sang `ContextVar` cấp module |
| F7 | `patch_mat_hang` gọi `item_detail` 3 lần và `get_references` 2 lần | Giảm còn số lần cần thiết |
| F8 | Router BOM tự viết lại `reject_body`, kiểm tra query trùng và đọc If-Match riêng | Dùng các hàm có sẵn trong `app.core.request_context` |
| F9 | Phát hiện hết dải mã bằng cách so chuỗi lỗi | Bỏ qua (D5) |
| F10 | Kiểm tra thừa, `ItemCode` không dùng, luôn UPDATE `is_active` | Dọn |

## Quyết định cần dev xác nhận

- **D1 – Nhánh, worktree, commit, push.**
  - Đề xuất: tạo worktree riêng `D:\Workspace\xbike-mrp-system-pr10` từ `origin/feature/catalog`. Lý do: checkout chính đang có thay đổi chưa commit (Sidebar, admin-ui, skill), không được động vào.
  - Merge `main` vào `feature/catalog` bằng merge commit, không rebase và không force push, vì đây là nhánh của tác giả PR (BonM2).
  - Sau khi kiểm chứng xong: 2 commit (merge, sửa review) rồi push `origin feature/catalog` để PR 10 tự cập nhật.
  - Phương án khác: nhánh mới `fix/pr10-catalog` và PR mới trỏ vào `feature/catalog`.
  - Cần dev cho phép rõ: commit merge, commit sửa, và push.
- **D2 – Thế nào là "đã dùng trong công thức" (UC-11 R1).**
  - Đề xuất: chỉ tính `ChiTietBom.mat_hang_id = :id`, tức mặt hàng là thành phần trong một công thức. Không tính `Bom.mat_hang_id`, vì đó là công thức của chính thành phẩm và luôn tồn tại từ UC-16.
  - Giữ nguyên quy tắc của PR: SKU bị khóa khi `has_any` (thành phần công thức, chứng từ, tồn kho).
- **D3 – Trạng thái mặt hàng và công thức lệch nhau** (thành phẩm active nhưng không có phiên bản đang dùng, hoặc ngược lại).
  - Đề xuất: trả **409 `ConflictException`** "Trạng thái thành phẩm và công thức không khớp". Không tự sửa dữ liệu, vì spec không mô tả trường hợp này (AGENTS.md: không tự đặt nghiệp vụ).
  - Phương án khác: tự đồng bộ, tức vẫn đặt `is_active` và ghi audit.
- **D4 – Frontend (đã chốt).** Chỉ sửa BE, không sửa FE.
  - Giới hạn đã biết: sau khi merge, MaterialsPage và BOMPage vẫn lệch hợp đồng API mới (F2, F3) cho đến khi có người sửa FE.
- **D5 – F9 (so chuỗi lỗi hết dải mã).**
  - Đề xuất: bỏ qua. Sửa đúng cách cần đổi trigger `init.sql` sang `ERRCODE` riêng, mà DB đang chạy không tự cập nhật (AGENTS.md §DB), nên mapping theo sqlstate sẽ hỏng trên DB cũ.
  - Ghi lại như một giới hạn đã biết.

## Bước 0 – Claude làm trước khi gọi Codex (sau khi D1 được duyệt)

1. `git worktree add D:\Workspace\xbike-mrp-system-pr10 -b feature/catalog origin/feature/catalog`. Nếu nhánh local đã tồn tại thì dùng nhánh đó.
2. Baseline trên PR chưa merge: chạy pytest toàn backend và ghi số pass/skip/fail.
3. `git merge main` và giải xung đột:

| File | Cách giải |
|---|---|
| `backend/app/modules/audit/schemas.py` | Lấy bản `main` (đã chứa đủ `ThaoTac` v4 và `trang_thai_*` bắt buộc trong `AuditLogResponse`). Xóa khai báo `trang_thai_truoc/sau` trùng trong `CreationAudit`. |
| `backend/app/modules/audit/models.py` (tự merge) | Xóa cặp `trang_thai_truoc/sau` trùng ở cuối class, giữ vị trí của `main`. |
| `backend/app/modules/mat_hang/models.py` (tự merge) | Giữ `so_luong_dang_giu`/`so_luong_con_dung` của `main`. Xóa khối trùng của PR. Giữ `created_at`. |
| `backend/app/modules/bom/repository.py` | Dùng `from app.modules.san_xuat.models import YeuCauSanXuat` và `_used = exists().where(YeuCauSanXuat.bom_id == Bom.id)` của `main`. Giữ import `BomContext`, `MatHangRead` và `_context` của PR. Bỏ import `table`, `column` không còn dùng. |
| `backend/app/modules/mat_hang/repository.py` | Lấy danh sách bảng của PR (v4: `GiuHang`, `NhuCauLinhKien`). Bản `main` tham chiếu `ChiTietPhieuDieuChinhKho` và `ChiTietTicketLoiDieuChinh`, hai bảng không có trong `init.sql` v4. |
| `docs/sequence/bom.md` | Lấy bản PR (mô tả v4), rồi kiểm tra không còn chữ `LenhSanXuat`. |

4. Sửa fixture `backend/tests/test_uc23_lap_gui_yeu_cau_san_xuat.py`: thêm `so_luong_dang_giu=reservations[id_]` và `so_luong_con_dung=inventory[id_] - reservations[id_]`. Đây chỉ là đồng bộ hợp đồng DTO, không đổi assert.
5. Chạy `ruff check` trên các file đã giải xung đột, cùng pytest toàn backend. Ghi baseline sau merge vào mục Kết quả. Lỗi mới do merge thì sửa trong bước này.
6. Commit merge (D1): `Merge branch 'main' into feature/catalog`.

## Phase 1 – Backend (Codex thực thi)

| File | Thay đổi |
|---|---|
| `backend/app/modules/mat_hang/repository.py` | F4/D2: `has_bom` chỉ còn `EXISTS (SELECT 1 FROM "ChiTietBom" WHERE mat_hang_id=:id)`. |
| `backend/app/modules/mat_hang/service.py` | F7: gọi `get_references` tối đa một lần cho mỗi request, chỉ khi `update` có `sku` hoặc `don_vi_tinh`. Chỉ đọc lại `item_detail` làm `previous` khi trạng thái đã bị đổi qua stop/reuse; nếu không thì dùng `before`. F10: bỏ `update["don_vi_tinh"] != before.don_vi_tinh` thừa. |
| `backend/app/modules/mat_hang/schemas.py` | F10: bỏ alias `ItemCode` nếu không còn ai dùng (kiểm tra bằng grep). |
| `backend/app/modules/mat_hang/mutation.py` | F6: một `ContextVar` cấp module (`_ACTIVE_MUTATION: ContextVar[MatHangMutation \| None]`). `require_active` kiểm tra `_ACTIVE_MUTATION.get() is self`. `scope` báo lỗi lồng nhau khi biến này khác `None`. Giữ nguyên thứ tự khóa cache → transaction và logic publish/mark_unavailable. |
| `backend/app/modules/bom/service.py` | F5/D3: `stop_for_item_in_transaction` raise `ConflictException` khi item active mà `context.active is None`. `reuse_last_for_item_in_transaction` raise `ConflictException` khi `context.active` không `None` (item đang ngừng nhưng còn phiên bản đang dùng). F10: `create_version`/`_activate` chỉ gọi `items.update(..., {"is_active": True})` khi `before.item.is_active` là False. Khi đó `create_version` lấy item cho `changes` từ `after.item`. |
| `backend/app/modules/bom/router.py` | F8: xóa `reject_body` cục bộ, dùng `app.core.request_context.reject_body`. Thay khối kiểm tra `multi_items` trong `list_bom` bằng `Depends(reject_repeated_query)`. `create_version`, `delete_bom`, `activate_bom` đọc If-Match bằng `Depends(get_strong_if_match)`. Mã HTTP giữ nguyên (422/412/428). |
| `docs/sequence/mat_hang.md` | PATCH/DELETE: thêm nhánh 409 trạng thái lệch (D3). Sửa mô tả điều kiện đổi đơn vị tính (D2). |
| `docs/sequence/bom.md` | Thêm nhánh 409 trạng thái lệch nếu sơ đồ có luồng stop/reuse theo mặt hàng. |

Không gắn thêm comment UC vào hàm phụ trợ. Chỉ giữ hoặc cập nhật docstring UC sẵn có của các hàm public đã sửa.

### Bảng test ↔ phát hiện

| Test | File | Assert |
|---|---|---|
| UC-11 AC-1: thành phẩm mới (có BOM v1, chưa dùng) đổi được đơn vị tính | `backend/tests/test_catalog_postgres.py` (chỉ chạy khi có `GOODS_ISSUE_TEST_DATABASE_URL`) | PATCH `don_vi_tinh` trả 200, giá trị mới được lưu |
| UC-11 AC-2: linh kiện đã nằm trong công thức không đổi được đơn vị tính | `test_catalog_postgres.py` (giữ hoặc bổ sung) | 409 |
| D2 ở mức service | `backend/tests/test_catalog_service.py` | Với repository giả có `has_bom=False, has_docs=False`, PATCH `don_vi_tinh` của thành phẩm thành công; với `has_bom=True` thì 409 |
| D3: ngừng thành phẩm active nhưng không có phiên bản đang dùng | `backend/tests/test_bom_service.py` | `stop_for_item_in_transaction` raise `ConflictException`, không gọi `items.update` |
| D3: dùng lại thành phẩm đang ngừng nhưng còn phiên bản đang dùng | `test_bom_service.py` | `reuse_last_for_item_in_transaction` raise `ConflictException` |
| F6: gọi lồng scope bị chặn; `require_active` ngoài scope báo lỗi | `backend/tests/test_mat_hang_bom.py` | `RuntimeError` trong cả hai trường hợp; sau khi scope kết thúc thì `require_active` lại báo lỗi |
| F8: hợp đồng lỗi BOM giữ nguyên | `test_bom_api.py` hiện có (`test_bom_ac07_*`, `test_uc18_ac6_*`) | Vẫn pass, không làm yếu test |
| F10: tạo phiên bản cho thành phẩm đang active không UPDATE `MatHang` | `test_bom_service.py` | Fake `items.update` không bị gọi khi item đã active, và bị gọi đúng một lần khi item đang ngừng (UC-17 R3) |
| D2 ảnh hưởng UC-29 D6 | `backend/tests/test_uc29_bat_dau_san_xuat.py::test_item_reference_sql_excludes_order_tables` | Bỏ `"Bom"` khỏi tập bảng kỳ vọng; giữ nguyên các assert khác |

## Ràng buộc cho Codex

- Đọc `AGENTS.md` trước. Làm việc **chỉ trong worktree** `D:\Workspace\xbike-mrp-system-pr10`.
- Chỉ sửa các file trong bảng Phase 1 và bảng test. Nếu buộc phải sửa file khác thì dừng và báo lý do.
- Không commit, không push, không migration, không sửa `init.sql`/`seed.sql`, không động DB/Docker, không đổi dependency hay lockfile, không sửa frontend.
- Không làm yếu hay xóa test sẵn có. Không sửa test fail sẵn ngoài phạm vi (theo baseline sau merge).
- Python: `D:\Workspace\xbike-mrp-system\backend\.venv\Scripts\python`, chạy từ `<worktree>\backend`.
- Chỉ chạy test liên quan và ruff trên file đã sửa (lệnh bên dưới). Báo file đã sửa, kết quả thực tế từng lệnh, và mọi điểm lệch plan. Không sửa mục "Kết quả" của plan.

## Lệnh kiểm chứng

Codex:

```bash
cd D:/Workspace/xbike-mrp-system-pr10/backend && D:/Workspace/xbike-mrp-system/backend/.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_catalog_service.py tests/test_catalog_api.py tests/test_bom_service.py tests/test_bom_api.py tests/test_mat_hang_bom.py tests/test_uc23_lap_gui_yeu_cau_san_xuat.py
```

```bash
cd D:/Workspace/xbike-mrp-system-pr10/backend && D:/Workspace/xbike-mrp-system/backend/.venv/Scripts/python -m ruff check <file đã sửa>
```

Claude chạy thêm toàn bộ backend để so với baseline sau merge:

```bash
cd D:/Workspace/xbike-mrp-system-pr10/backend && D:/Workspace/xbike-mrp-system/backend/.venv/Scripts/python -m pytest -q -p no:cacheprovider
```

## Điều kiện đạt

- Test trong bảng test ↔ phát hiện đều pass. Test PostgreSQL được ghi là skip nếu không có DB test.
- Toàn backend không có fail mới so với baseline sau merge.
- `ruff` sạch trên các file đã sửa.
- `git diff` chỉ chạm các file trong plan.

## Commit dự kiến (sau khi đạt và có phép theo D1)

1. `Merge branch 'main' into feature/catalog` (Bước 0).
2. `fix(catalog): sửa phát hiện review PR 10 — tham chiếu công thức, trạng thái lệch, ContextVar, router BOM`

Push `origin feature/catalog` (không force).

## Ngoài phạm vi

- Frontend MaterialsPage và BOMPage (D4: dev chốt chỉ sửa BE).
- F9: so chuỗi lỗi hết dải mã (D5).
- Gộp ba hàm kiểm tra vai trò (`_require_reader`, `_require_role`, `require_supplier_role`) thành một helper chung: chỉ là dọn dẹp, để sau.
- Module `dieu_chinh_kho` legacy trên `main` (dùng thao tác hoặc bảng không có trong v4).

## Kết quả

### Bước 0 (Claude, 16/11/2026)

- Worktree `D:\Workspace\xbike-mrp-system-pr10`, nhánh `feature/catalog` (e6a1cab).
- Baseline PR chưa merge: 72 pass, 171 skip, 8 fail. Cả 8 fail nằm ở `test_nhan_vien_create_code.py`, là lỗi sẵn có của base cũ và đã được `main` sửa.
- Merge `main`, giải xung đột theo bảng Bước 0. Cập nhật thêm `test_uc29_bat_dau_san_xuat.py::test_item_reference_sql_excludes_order_tables` vì danh sách bảng trên `main` vẫn có hai bảng không còn trong v4.
- Sau merge: 829 pass, 255 skip, 0 fail. `ruff` sạch trên các file đã giải xung đột.
- Merge commit `40e180c`.

### Phase 1 (Codex thực thi, Claude kiểm chứng, 16/11/2026)

File code đã sửa: `bom/router.py`, `bom/service.py`, `mat_hang/mutation.py`, `mat_hang/repository.py`, `mat_hang/schemas.py`, `mat_hang/service.py`.
Test: `test_bom_service.py`, `test_catalog_service.py`, `test_mat_hang_bom.py`, `test_catalog_postgres.py`, `test_uc29_bat_dau_san_xuat.py`.
Docs: `docs/sequence/mat_hang.md`, `docs/sequence/bom.md`.

| Phát hiện | Test | Kết quả |
|---|---|---|
| F4/D2 | `test_catalog_service.py` (SKU vẫn khóa theo mọi tham chiếu); `test_catalog_postgres.py::test_finished_item_with_initial_formula_can_change_unit` (UC-11 AC-1), `::test_formula_component_cannot_change_unit` (UC-11 AC-2) | Service pass. Test PostgreSQL skip vì không có DB test |
| F5/D3 | `test_bom_service.py::test_stop_rejects_active_item_without_active_formula`, `::test_reuse_rejects_stopped_item_with_active_formula`, `::test_item_lifecycle_without_versions_keeps_conflict` | Pass |
| F6 | `test_mat_hang_bom.py::test_mutation_scope_rejects_nesting_and_checks_owner`, `::test_mutation_scope_resets_owner_after_error` | Pass |
| F7 | `test_catalog_service.py::test_patch_reads_only_required_snapshots`, `::test_patch_state_and_description_refreshes_previous` | Pass |
| F8 | `test_bom_api.py` hiện có (`test_bom_ac07_*`, `test_uc18_ac6_*`) | Skip (cần PostgreSQL); kiểm bằng đọc diff, mã lỗi vẫn là 422/412/428 |
| F10 | `test_bom_service.py::test_create_version_updates_only_stopped_item`, `::test_activate_version_updates_only_stopped_item` | Pass |

- Các test liên quan (Codex chạy): 182 pass, 173 skip, 0 fail. `ruff` sạch trên 11 file Python.
- Toàn backend (Claude chạy lại): 852 pass, 257 skip, 0 fail. Trước Phase 1 là 829 pass, 255 skip.
- Diff chỉ chạm file trong plan. Không có test nào bị làm yếu: các dòng bị xóa chỉ là import được gộp và dòng `"Bom"` trong UC-29 D6.
- Giới hạn còn lại:
  - Test PostgreSQL và API của BOM/catalog chưa chạy trên DB thật. Fixture dùng `BOM_TEST_DATABASE_URL` hoặc `GOODS_ISSUE_TEST_DATABASE_URL`.
  - FE vẫn lệch API (F2, F3) theo D4.
  - F9 bỏ qua theo D5.

### Merge origin/main lần 2 (16/11/2026)

`origin/main` đã có PR 9 (`feature/bom`, gồm `b3923d6`) và PR 8 (`feature/phieu_nhap`). Dev chốt: theo bản main, bỏ D3.

- **BOM** (`bom/router.py`, `bom/service.py`, `test_bom_service.py`, `test_mat_hang_bom.py`, `docs/sequence/bom.md`): lấy bản main. Các thay đổi D3/F6/F7/F8/F10 của Phase 1 trên các file này bị thay bằng bản PR 9, vốn đã xử lý F6, F7, F8 và đồng bộ trạng thái theo UC-12 R3.
- **`mat_hang/service.py`, `mat_hang/mutation.py`, `docs/sequence/mat_hang.md`:** lấy bản main, rồi áp lại phần catalog của `e6a1cab` (PR 10):
  - reader UC-09 có kiểm quyền và `MatHangListQuery`;
  - PATCH chỉ ghi các trường thực sự đổi, no-op không publish cache;
  - khóa SKU khi có tham chiếu hoặc tồn; `get_references` gọi tối đa một lần.
  - Lần giải xung đột đầu lấy nguyên bản main nên làm mất phần này. Lỗi đó đã được phát hiện và sửa trước khi commit.
- **D2 giữ nguyên** (`has_bom` chỉ xét `ChiTietBom`). `test_uc29` bỏ `"Bom"` khỏi tập bảng.
- **Phiếu nhập:** giữ thiết kế đọc và khóa của PR 8, ghép phần UC-44 của PR 10: `nha_cung_cap` nạp bằng selectin ở list, detail và lock; audit loại `nha_cung_cap`; docs bổ sung ghi chú NCC.
- **Test:**
  - `conftest.py`: fake tạo phiếu thêm NCC (Codex).
  - `test_bom_service.py`: fixture `MatHangRead` thêm `so_luong_dang_giu` và `so_luong_con_dung`.
  - `test_uc20...::test_ac5_delete_audits_actor_time_and_draft_state`: so audit với response trừ `nha_cung_cap`, theo thiết kế UC-44.
  - `test_catalog_service.py`: fixture dùng `boms.lock_item` thay cho cách khóa cũ, giảm số lần `item_detail` kỳ vọng tương ứng; giữ nguyên ý nghiệp vụ.
- **Kết quả:** toàn backend 906 pass, 323 skip, 0 fail. `ruff` sạch trên các file đã sửa.
