---
name: thuc-thi-uc
description: Thực thi từng use-case (UC-xx) của xBike MRP theo quy trình plan → dev duyệt → Codex thực thi → Claude kiểm chứng theo UC → test AC pass → commit/push. Dùng khi dev yêu cầu "thực thi UC", "triển khai UC-xx", "làm UC tiếp theo" hoặc chạy lần lượt các UC của một bounded context (identity_access, catalog, ...).
---

# Thực thi use-case qua Codex

Quy trình dev chốt ngày 15/11/2026. Làm **từng UC một**, theo thứ tự mã UC trong bounded context, không gộp nhiều UC vào một plan hay một commit.

Luôn tuân `AGENTS.md`: hỏi lại khi chưa rõ, không tự đặt nghiệp vụ, không xóa/seed lại DB, không đổi dependency/lockfile khi chưa được phép.

## Vòng lặp cho mỗi UC

### 1. Đọc và khảo sát

- Spec: `specs/use_cases/{context}/UC-xx.md` (quy tắc R#, AC, Main flow, Alternative Flow).
- BR liên quan trong `specs/business_requirements/BR-GIAIDOAN1.md`; `specs/entity_model/{data_model_v4,entity_model}.md`; `infra/postgres/init.sql`.
- Code hiện có: `backend/app/modules/<module>/{router,service,schemas,repository,models,ports}.py`, `backend/app/dependencies.py`, FE `frontend/src/features/...`, test hiện có.
- Plan của UC trước trong `docs/plans/` để giữ quyết định đã chốt (vd. D2 của UC-01 dời `phien_ban_dang_nhap` sang UC-07).
- Chạy baseline và ghi số liệu (xem mục Kiểm chứng).

### 2. Lập plan — `docs/plans/UC-xx.md`

Theo khuôn `docs/plans/UC-01.md`, gồm:

- Goal; Context read.
- **Bảng hiện trạng so với UC**: mỗi R/bước/luồng A → hiện trạng code → việc cần làm.
- **Quyết định cần dev xác nhận** (D1, D2, …) kèm đề xuất. Mọi điểm spec/code/data model lệch nhau hoặc spec chưa nói rõ phải nằm ở đây, không tự chọn.
- Quy ước comment UC (mục bên dưới).
- Backend: bảng file → thay đổi. Frontend: bảng file → thay đổi.
- **Bảng test ↔ AC**: mỗi AC (và luồng A quan trọng không có AC) có ít nhất một test, ghi rõ assert gì.
- Tài liệu: `docs/sequence/<module>.md` khi endpoint thay đổi (AGENTS.md §8).
- Ràng buộc cho Codex; lệnh kiểm chứng; điều kiện đạt; message commit dự kiến; ngoài phạm vi; mục "Kết quả: _Chưa thực thi._".

Báo dev tóm tắt plan + các D cần chốt, rồi **dừng chờ duyệt**. Không chạy Codex khi chưa có câu duyệt rõ ràng của dev trong chat. Khi duyệt, ghi vào đầu plan: "dev đã duyệt <ngày> (…)".

### 3. Gọi Codex

Viết prompt vào scratchpad, chạy nền (codex-cli 0.167: **không còn `--full-auto`**, và `--sandbox` không đi cùng `--approve-for-me`):

```bash
codex exec -s workspace-write -C "<repo>" -o "<scratchpad>/codex-uc-xx-last.md" - < "<scratchpad>/codex-uc-xx-prompt.md" > "<scratchpad>/codex-uc-xx.log" 2>&1
```

Prompt cho Codex phải nêu:

- Thực thi plan đã duyệt `docs/plans/UC-xx.md`, spec `specs/use_cases/{context}/UC-xx.md`; đọc `AGENTS.md` trước.
- Các D đã duyệt thế nào; D nào không làm.
- Quy ước comment UC và comment test (nguyên văn mục bên dưới).
- Không commit, không push, không migration, không động DB/Docker/seed, không đổi dependency/lockfile, chỉ sửa file trong plan (nếu buộc phải sửa file khác thì báo lý do).
- Không sửa test fail sẵn ngoài phạm vi UC (liệt kê theo baseline).
- Python: `backend/.venv/Scripts/python`; FE: `npm test` trong `frontend/`.
- Chạy đủ lệnh kiểm chứng, báo file đã sửa, kết quả thực tế từng lệnh, điểm lệch plan. Không sửa mục "Kết quả" của plan.

Codex chạy nền: không theo dõi, không poll log, không can thiệp giữa chừng; trong lúc chờ có thể làm việc khác không đụng file của UC. Khi có thông báo Codex chạy xong: đọc `codex-uc-xx-last.md` và log. Nếu exit lỗi do cờ CLI, xem `codex exec --help` và chạy lại.

### 4. Kiểm chứng (Claude làm, không tin báo cáo của Codex)

- `git diff` toàn bộ: chỉ đúng file trong plan; không có thay đổi ngoài phạm vi, không đổi lockfile.
- Đối chiếu từng R, bước Main flow, luồng A của spec với code thật (status code, mã lỗi, transaction, audit, quyền).
- Mỗi hàm router/service tham gia UC có comment UC đúng bước/luồng.
- Mỗi test có comment `UC-xx AC-n` / `UC-xx A<n>`; đủ mọi AC trong bảng test ↔ AC; assert đúng ý AC (không assert lỏng, không test rỗng, không làm yếu test cũ).
- Tự chạy lại các lệnh kiểm chứng và đọc kết quả.
- Lệch hoặc thiếu: sửa nhỏ trực tiếp, hoặc gửi Codex một prompt sửa cụ thể rồi kiểm chứng lại. Lệch nghiệp vụ chưa rõ → hỏi dev.

### 5. Commit và push

Chỉ khi **toàn bộ test ứng với AC pass** và không có lỗi mới so với baseline:

- Điền mục "Kết quả" trong plan (file đã sửa, số pass/fail từng lệnh, bảng AC → test → kết quả, giới hạn còn lại).
- `git add` đúng các file của UC (code, test, docs, plan) — không `git add -A` mù.
- Commit message: `feat(UC-xx): <mô tả ngắn tiếng Việt>`, kết thúc bằng dòng `Co-Authored-By` theo chỉ dẫn attribution hiện hành.
- Push lên nhánh đang làm: `git push -u origin <nhánh>` lần đầu, sau đó `git push`. Không force push.
- Báo dev kết quả, rồi chuyển sang lập plan UC kế tiếp (quay lại bước 1). Không tự chạy Codex cho UC kế tiếp khi chưa được duyệt.

Nếu test AC không pass được: không commit, báo dev test nào fail, nguyên nhân, đề xuất.

## Quy ước comment UC (bắt buộc)

- Hàm router/service: comment ngay trên định nghĩa hàm
  `# UC-xx <Tên UC> — <bước/luồng: Main 2–6; A2, A3> (specs/use_cases/{context}/UC-xx.md)`
- Test: comment ngay trên hàm test `# UC-xx AC-n: <tên AC>` hoặc `# UC-xx A<n>: <tên luồng>`.
- File test mới đặt tên theo UC: `backend/tests/test_ucxx_<ten>.py`, `frontend/tests/ucxx-<ten>.test.js`.

## Kiểm chứng và điều kiện đạt

Mức test dev đã chọn: **BE pytest với repository giả (ASGI, không DB) + FE `node --test`**. Không bắt buộc Playwright hay PostgreSQL thật trừ khi dev yêu cầu.

```bash
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_ucxx_<ten>.py
cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider
cd backend && .venv/Scripts/python -m ruff check <file đã sửa>
cd frontend && npm test
cd frontend && npx eslint <file đã sửa>
```

Đạt khi: test của UC pass 100%; toàn backend và FE không có lỗi mới so với baseline; ruff/eslint sạch trên file đã sửa.

Baseline mới nhất trên `identity_access` (sau UC-08): backend 326 pass, 22 skip (PostgreSQL), 0 fail; frontend 134 pass. Cập nhật baseline sau mỗi UC đã commit.

Bài học khi chạy identity_access: Codex có xu hướng gắn comment UC tràn lan vào hàm phụ trợ — trong plan hãy liệt kê **đích danh** các hàm được comment, và khi kiểm chứng gỡ comment ở hàm không thuộc luồng. Mỗi UC viết prompt Codex mới, không sửa từ prompt UC trước.

## Môi trường

- `backend/.venv` do uv tạo, không có pip: cài bằng `uv pip install --python backend/.venv/Scripts/python.exe ...` (không đổi manifest/lockfile).
- Nhánh hiện tại cho identity_access: `identity_access`, push `origin identity_access`.
