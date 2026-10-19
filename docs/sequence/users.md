# Sequence diagram — users

Hai endpoint `GET /api/v1/nhan_vien` và `GET /api/v1/nhan_vien/{id}`
được `main.py` đăng ký từ module `nhan_vien`.
Luồng hiện tại được mô tả tại [nhan_vien.md](nhan_vien.md).

Module `users` đã được chuyển sang `nhan_vien`. ORM `User` và `Role` nằm trong
`nhan_vien.models` và được dùng chung với xác thực. File này giữ liên kết tài liệu cũ.
