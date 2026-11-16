# Plan sửa PR 8 — phiếu nhập (UC-20, UC-21, UC-22)

Trạng thái: **dev đã duyệt 16/11/2026** ("Gọi codex thực thi" — theo đúng đề xuất D1–D7). Chưa commit.

Ghi chú thực thi: làm trong worktree `D:/Workspace/xbike-mrp-system-phieu-nhap` (nhánh `feature/phieu_nhap`). Claude đã chạy `git merge --no-ff --no-commit origin/main` và giải sẵn các file lấy bản main (`audit/models.py`, `audit/schemas.py`, `docs/sequence/audit.md`, 4 ảnh `assets/{audit,inventory}`). Còn xung đột: `inventory/ports.py`, `inventory/repository.py`, `tests/conftest.py`, `docs/sequence/inventory.md`. Merge và các thay đổi UC để chưa commit; commit theo UC sau khi dev cho phép.

## Goal

Đưa PR [thanhklt/xbike-mrp-system#8](https://github.com/thanhklt/xbike-mrp-system/pull/8) (`feature/phieu_nhap`, 1 commit `89a1007`) về trạng thái merge được vào `main` hiện tại (`af4cbfb`). Giữ nguyên phần nghiệp vụ phiếu nhập theo data model v4, sửa các lỗi đã review, rồi kiểm chứng lại theo spec `specs/use_cases/goods_receipt/UC-20.md`, `UC-21.md`, `UC-22.md` và quy trình `thuc-thi-uc`.

## Context đã đọc

- PR 8: diff backend (`phieu_nhap`, `inventory`, `audit`), test mới (`conftest.py`, `test_phieu_nhap_{api,postgres,service}.py`), docs (`docs/sequence/phieu_nhap.md`, `inventory.md`, `audit.md`, `specs/use_cases/goods_receipt/{README,PLAN}.md`).
- `main` (`af4cbfb`): spec UC-20..22 dạng mới, `docs/plans/UC-*.md`, `audit` đã lên v4 (UC-43), `inventory` có thêm `receive_production`, `lock_issue_stock`, `issue_stock` (UC-31, UC-34..40), `conftest.py` có fixture `goods_issue_*`, FE `ReceivingPage.jsx`.
- `infra/postgres/init.sql` ở cả hai nhánh đã là v4 (`nhap_linh_kien`, `so_luong_ton_sau`, `phien_ban`, `hoan_thanh_at`...). PR 8 không sửa `init.sql`.
- `AGENTS.md` (§1 không tự commit/push, §6 báo thay đổi hợp đồng API, §8 tài liệu sequence), skill `thuc-thi-uc`.

## Hiện trạng

| Hạng mục | `main` | PR 8 |
|---|---|---|
| Nhánh gốc | — | Tách từ `f461ecd`, sau đó main đã merge thêm PR #9 → #16 |
| `phieu_nhap/*` | Vẫn là bản v3 (tiền `Decimal`, chưa có `phien_ban`, `hoan_thanh_at`) | Đã lên v4 |
| `inventory.receive_receipt` | Ghi `'nhap_vat_tu'`, không ghi `so_luong_ton_sau`, nên **hỏng với `init.sql` v4** | Ghi `'nhap_linh_kien'` + `so_luong_ton_sau`, tách bước khóa thành `lock_receipt_stock` |
| `audit` models/schemas | Đã v4 đầy đủ (UC-43), có `trang_thai_truoc/sau` | Sửa một phần, trùng với main |
| Test | Không có test phiếu nhập | Test PostgreSQL bị skip khi thiếu `GOODS_RECEIPT_TEST_DATABASE_URL`; không có test repo giả theo AC |
| Spec/plan | `specs/use_cases/goods_receipt/UC-20..22.md` | `specs/use_cases/goods_receipt/README.md` + `PLAN.md` (định dạng cũ, GR-AC-01..22) |
| Comment UC | Quy ước `# UC-xx <Tên> — <bước> (specs/...)` | Docstring và `description="UC-22; specs/.../README.md"` trên router |

Kết quả `git merge-tree origin/main origin/feature/phieu_nhap` cho thấy xung đột ở `audit/models.py`, `audit/schemas.py`, `inventory/ports.py`, `inventory/repository.py`, `tests/conftest.py`, `docs/sequence/{audit,inventory}.md` và 4 ảnh trong `docs/sequence/assets/{audit,inventory}/`. Không có xung đột trong `phieu_nhap/*` vì main chưa sửa module này kể từ `f461ecd`.

## Quyết định cần dev xác nhận

- **D1 — Cách đồng bộ với main.** Đề xuất: **merge `origin/main` vào `feature/phieu_nhap`** (repo đã dùng cách này, ví dụ "Merge branch 'main' into feature/bom"). Cách này giữ PR 8 và không phải force push. Phương án khác là rebase rồi force push, nhưng làm vậy trái với quy ước "không force push" nên không đề xuất.
- **D2 — Tài liệu spec của PR.** `specs/use_cases/goods_receipt/README.md` và `PLAN.md` trùng vai trò với `UC-20..22.md` và `docs/plans/`. Đề xuất: bỏ hai file này khỏi PR, chuyển những quyết định còn giá trị (ETag, idempotent, tiền BIGINT) vào chính plan này. Nếu dev muốn giữ thì ghi rõ chúng là tài liệu phụ.
- **D3 — Mức test.** Theo `thuc-thi-uc`, mức bắt buộc là pytest với repository giả (ASGI, không DB). Đề xuất: thêm `test_uc20_*`, `test_uc21_*`, `test_uc22_*` với repository giả, mỗi AC có ít nhất một test; giữ `test_phieu_nhap_postgres.py` làm test tùy chọn (opt-in). Chưa có PostgreSQL test thì chỉ báo số test bị skip, không coi là đã đạt.
- **D4 — Ai được xem phiếu nhập (UC-22, mục "Điểm cần làm rõ").** Hiện tại chỉ `quan_ly` xem được; Quản trị viên và Nhân viên nhận 403. Đề xuất giữ nguyên, khớp UC-22 R1/R2.
- **D5 — Gửi lại hoàn tất cho phiếu đã hoàn tất (UC-21 AC-3).** Hiện tại nhánh này chỉ kiểm tra định dạng `If-Match`, không so với ETag. Đây là điều kiện cần để request gửi lại (vẫn mang ETag bản nháp cũ) nhận 200 mà không cộng tồn lần nữa. Đề xuất **giữ nguyên hành vi**, thêm comment giải thích và test AC-3. Kết quả review số 6 vì vậy chuyển thành "không cần sửa".
- **D6 — Kiểm tra trong `receive_receipt`.** Main dùng mẫu "chính sách và khóa thuộc use case" (`issue_stock`), nên PR bỏ kiểm tra trong `receive_receipt` là đúng mẫu. Đề xuất chỉ thêm một chốt rẻ: nếu `UPDATE ... RETURNING` trả `None` thì raise `ConflictException`, để tránh lỗi 500 do `so_luong_ton_sau` NULL.
- **D7 — Kiểm tra quyền ở service (`_require_manager`).** `phieu_xuat` cũng kiểm tra quyền ở service (`_role`), nên đây là quy ước sẵn có. Đề xuất giữ, bỏ trùng ở router: endpoint đã có `actor` thì không cần thêm `Depends(receipt_actor)` ở cấp `APIRouter`, hoặc ngược lại. Chọn một tầng tại router, giữ service làm lớp phòng thủ.

## Giai đoạn 0 — Đồng bộ với main (theo D1)

Làm trong worktree riêng để không đụng các thay đổi chưa commit đang có trên `main` local (Sidebar, admin-ui...):

```bash
git worktree add ../xbike-phieu-nhap feature/phieu_nhap
```

```bash
git -C ../xbike-phieu-nhap merge origin/main
```

Giải xung đột:

| File | Cách giải |
|---|---|
| `backend/app/modules/audit/models.py`, `audit/schemas.py` | Lấy bản main (đã chứa mọi thay đổi PR cần và `ThaoTac` v4). Kết quả review số 3 được xử lý ở đây. |
| `backend/app/modules/inventory/ports.py` | Gộp: giữ `IssueReservation`, `IssueStockContext`, `InventoryIssueWriter`, `receive_production` của main; thêm `ReceiptStock` và `lock_receipt_stock` vào `InventoryWriter`. |
| `backend/app/modules/inventory/repository.py` | Giữ `receive_production`, `lock_issue_stock`, `issue_stock`, `lock_balances`, `adjust_stock` của main. Thay `receive_receipt` cũ của main (`nhap_vat_tu`) bằng bản của PR, thêm `lock_receipt_stock`. Bỏ import thừa nếu ruff báo. |
| `backend/tests/conftest.py` | Gộp cả hai bộ fixture `goods_issue_*` và `goods_receipt_*`; không đổi hành vi của fixture `goods_issue_*`. |
| `docs/sequence/audit.md`, 4 ảnh `assets/{audit,inventory}` | Lấy bản main. |
| `docs/sequence/inventory.md` | Lấy bản main, rồi cập nhật đoạn ghi sổ nhập kho (`nhap_linh_kien`, `so_luong_ton_sau`, `lock_receipt_stock`) nếu main chưa có. |

Sau khi giải xong, chạy baseline: toàn bộ backend pytest, `npm test`, ruff các file vừa gộp. Ghi số pass/skip/fail làm baseline. Commit merge chỉ khi dev cho phép (AGENTS.md §1).

## Giai đoạn 1 — UC-20: Lập, sửa, xóa phiếu nhập nháp

| R/AC | Hiện trạng (PR sau merge) | Việc cần làm |
|---|---|---|
| R1, R3 / AC-1 | `create_receipt` không ghi tồn | Test: tạo nháp, tồn không đổi |
| R2 / AC-2 | `_validate_parts` chỉ nhận `linh_kien` đang hoạt động | Test: thêm thành phẩm thì nhận 409 `phu_thuoc_khong_hop_le` |
| R2 / AC-3 | `validate_lines` chặn trùng `mat_hang_id` | Test: dòng lặp thì nhận 422 |
| R4 / AC-4 | `_require_editable` | Test: sửa/xóa phiếu `hoan_thanh` bị từ chối |
| R6 / AC-5 | `_audit_change("xoa_nhap")` | Test: audit `xoa_nhap` có `nhan_vien_id`, `created_at`, `trang_thai_truoc='nhap'` |
| Review số 4 | So sánh `chi_tiet` theo thứ tự danh sách | So sánh theo `mat_hang_id` (dict hoặc sort) cho `current`, payload và `tong_gia`. Test: gửi lại cùng dòng nhưng đảo thứ tự thì không audit, không tăng `phien_ban`, ETag không đổi |
| Review số 5 | `_validate_parts` chạy cả khi dòng không đổi | Chỉ validate khi `chi_tiet` thật sự đổi. Test: linh kiện bị ngừng, PATCH chỉ sửa `ghi_chu` kèm `chi_tiet` cũ thì 200 |
| Review số 9 | `_validate_stock` lặp kiểm tra của `_validate_parts`, khác mã lỗi | Tách một hàm kiểm tra loại/hoạt động dùng chung; thống nhất mã lỗi khi thiếu mặt hàng (đề xuất 409 `phu_thuoc_khong_hop_le` ở cả hai) |

## Giai đoạn 2 — UC-21: Hoàn tất phiếu nhập

| R/AC | Hiện trạng | Việc cần làm |
|---|---|---|
| R1 / AC-1 | FE `confirmAction` hiện mã phiếu, ngày, các dòng (`SavedLines` có ĐVT), tác động kho | Test FE: đóng hộp xác nhận thì không gọi API |
| R2 / AC-2 | `mark_completed` + `receive_receipt` trong một transaction | Test: tồn 10, nhập 50 thì tồn 60, có `GiaoDichKho` `nhap_linh_kien`, `so_luong_ton_sau=60` |
| R2 / AC-3 | Nhánh `already_posted` trả 200, `da_ghi_so_truoc_do=true` | Theo D5: giữ, thêm comment; test gọi hai lần thì tồn chỉ tăng 50 |
| R3 / AC-4 | Không có code đụng `YeuCauSanXuat` | Test: yêu cầu `cho_bo_sung` giữ nguyên trạng thái sau khi hoàn tất |
| R4 / AC-5 | ETag + `phien_ban` trong `mark_completed` | Test: sửa ở phiên khác rồi hoàn tất bằng ETag cũ thì nhận 412, tồn không đổi; FE hiện thông báo yêu cầu xem lại |
| R5 | `_audit_change("hoan_tat")` có `trang_thai_truoc/sau` | Test: audit `nhap` → `hoan_thanh` |
| D6 | `receive_receipt` không kiểm tra kết quả `UPDATE` | Thêm chốt `None` → `ConflictException` |

## Giai đoạn 3 — UC-22: Xem phiếu nhập

| R/AC | Hiện trạng | Việc cần làm |
|---|---|---|
| R1 / AC-1 | `list_receipts` trả cả `nhap` và `hoan_thanh` trong snapshot chỉ đọc | Test: danh sách có cả hai trạng thái |
| R2 / AC-2 | `require_roles(["quan_ly"])` + `_require_manager` | Test: admin gọi list/detail thì 403; FE route chặn admin |
| D7 | Kiểm tra quyền ở cả router và từng endpoint | Bỏ một tầng trùng ở router |

## Việc chung cho cả ba UC

- **Comment UC:** thay docstring `"""UC-20..22; specs/.../README.md"""` và `description="UC-xx; specs/..."` trên router bằng comment theo quy ước, chỉ đặt ở đích danh các hàm sau:
  - router: `list_receipts`, `get_receipt` (UC-22); `create_receipt`, `patch_receipt`, `delete_receipt` (UC-20); `complete_receipt` (UC-21);
  - service: các hàm cùng tên.
- **Tài liệu:** `docs/sequence/phieu_nhap.md` khớp code sau khi sửa (quyền, 412/428, idempotent); `inventory.md` theo Giai đoạn 0.
- **Mô tả PR (review số 10, AGENTS.md §6):** viết lại phần mô tả PR, nêu các thay đổi hợp đồng API: tiền từ `Decimal`/chuỗi sang số nguyên VND (strict int); bỏ `ma_phieu_nhap` khỏi body tạo; response thêm `updated_at`, `hoan_thanh_at`, `nguoi_hoan_thanh_id`, `phien_ban`; `loai_giao_dich` đổi thành `nhap_linh_kien`; ETag tính theo JSON chuẩn hóa. Kèm cách kiểm chứng.

## File dự kiến sửa

| File | Thay đổi |
|---|---|
| `backend/app/modules/inventory/{ports,repository}.py` | Giải xung đột (Giai đoạn 0), chốt D6 |
| `backend/app/modules/audit/{models,schemas}.py` | Lấy bản main |
| `backend/app/modules/phieu_nhap/service.py` | Review số 4, 5, 9; comment UC; comment D5 |
| `backend/app/modules/phieu_nhap/router.py` | Bỏ `description=` chứa đường dẫn spec, thêm comment UC, D7 |
| `backend/tests/conftest.py` | Gộp fixture |
| `backend/tests/test_uc20_phieu_nhap_nhap.py`, `test_uc21_hoan_tat_phieu_nhap.py`, `test_uc22_xem_phieu_nhap.py` | Mới: test repository giả theo AC |
| `frontend/tests/uc21-hoan-tat-phieu-nhap.test.js` | Mới, nếu cần cho UC-21 AC-1/AC-5 phía FE |
| `docs/sequence/{phieu_nhap,inventory}.md` | Đồng bộ code |
| `specs/use_cases/goods_receipt/{README,PLAN}.md` | Theo D2 |

## Ràng buộc khi thực thi

- Không commit/push khi chưa được phép; không force push; không đụng DB ứng dụng, Docker, seed; không đổi dependency/lockfile.
- Không sửa `infra/postgres/init.sql` (đã v4 ở main).
- Mỗi UC một commit sau commit merge: `fix(UC-20): ...`, `fix(UC-21): ...`, `fix(UC-22): ...`.

## Kiểm chứng

```bash
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_uc20_phieu_nhap_nhap.py tests/test_uc21_hoan_tat_phieu_nhap.py tests/test_uc22_xem_phieu_nhap.py
```

```bash
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider
```

```bash
cd backend && .venv/Scripts/python -m ruff check app/modules/phieu_nhap app/modules/inventory tests/conftest.py
```

```bash
cd frontend && npm test
```

Đạt khi: mọi AC của UC-20..22 có test pass; backend/FE không có lỗi mới so với baseline Giai đoạn 0; ruff sạch; `git merge-tree origin/main feature/phieu_nhap` không còn xung đột.

## Ngoài phạm vi

- Tìm kiếm/lọc mới cho danh sách phiếu nhập (UC-22 chưa đặc tả).
- Trả hàng nhà cung cấp, gắn phiếu nhập với yêu cầu sản xuất (UC-20 ghi chú).
- Migration cho DB đang chạy.

## Kết quả

Thực thi 16/11/2026: Codex làm theo plan; Claude kiểm chứng lại. Chưa commit (merge `origin/main` đang ở trạng thái `--no-commit`, mọi xung đột đã được đánh dấu giải xong).

**File**

- Giải xung đột: `inventory/ports.py` (gộp, thêm `ReceiptStock`, `lock_receipt_stock`), `inventory/repository.py` (giữ method của main, thay `receive_receipt` bằng bản v4, thêm D6), `tests/conftest.py` (giữ `goods_issue_*`, `goods_receipt_*`, thêm fixture ASGI `receipt_api`), `docs/sequence/inventory.md`; lấy bản main cho `audit/models.py`, `audit/schemas.py`, `docs/sequence/audit.md`, 4 ảnh.
- Sửa: `phieu_nhap/service.py` (review 4, 5, 9; comment D5; comment UC), `phieu_nhap/router.py` (D7: bỏ dependency quyền cấp `APIRouter`, giữ `actor` ở 6 endpoint; bỏ `description=` cũ; comment UC đặt trên decorator như `san_xuat/router.py`), `tests/test_phieu_nhap_api.py` (mặt hàng thiếu 404 → 409), `docs/sequence/phieu_nhap.md`.
- Tạo: `tests/test_uc20_phieu_nhap_nhap.py`, `tests/test_uc21_hoan_tat_phieu_nhap.py`, `tests/test_uc22_xem_phieu_nhap.py`, `frontend/tests/uc21-hoan-tat-phieu-nhap.test.js`.
- Xóa (D2): `specs/use_cases/goods_receipt/README.md`, `PLAN.md`.

**Kiểm chứng (Claude tự chạy)**

| Lệnh | Baseline `origin/main` | Sau khi sửa |
|---|---|---|
| Backend pytest toàn bộ | 786 pass, 182 skip, 0 fail | 847 pass, 231 skip, 0 fail |
| Frontend `npm test` | 268 pass, 0 fail | 270 pass, 0 fail |
| Ruff (`inventory`, `phieu_nhap`, `conftest.py`, test UC-20..22, `test_phieu_nhap_api.py`) | — | Sạch |
| ESLint `uc21-hoan-tat-phieu-nhap.test.js` | — | Sạch |
| Marker xung đột | — | Không còn |

Skip tăng 49 là test PostgreSQL opt-in của phiếu nhập (thiếu `GOODS_RECEIPT_TEST_DATABASE_URL`).

**AC → test** (đều pass)

| AC | Test |
|---|---|
| UC-20 AC-1..5 | `test_uc20_phieu_nhap_nhap.py::test_ac1_..`, `test_ac2_..`, `test_ac3_..` (POST, PATCH), `test_ac4_..` (PATCH, DELETE), `test_ac5_..` |
| UC-21 AC-1 | FE `uc21-hoan-tat-phieu-nhap.test.js` (đóng hộp xác nhận không gọi API) |
| UC-21 AC-2..5, R5 | `test_uc21_hoan_tat_phieu_nhap.py::test_ac2_..` … `test_ac5_..`, `test_r5_..` |
| UC-22 AC-1, AC-2 | `test_uc22_xem_phieu_nhap.py::test_ac1_..`, `test_ac2_..` (admin, nhân viên × list, detail) |
| Review 4, 5, 9; D5; D6 | `test_reordered_lines_*`, `test_note_change_*`, `test_changed_line_*`, `test_missing_item_*`, `test_replay_still_requires_*`, `test_d6_*` |

**Giới hạn còn lại**

- Chưa chạy test PostgreSQL thật và E2E trình duyệt; Mermaid trong `docs/sequence` chưa render, chỉ đối chiếu với code.
- Thay đổi hợp đồng API mới: mặt hàng thiếu khi tạo/sửa trả 409 `phu_thuoc_khong_hop_le` thay vì 404.
- Chưa cập nhật mô tả PR 8 trên GitHub (review số 10).
