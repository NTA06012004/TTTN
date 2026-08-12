# Testing và Release Checklist

## Phạm vi test hiện có

- `tests/test_etl.py`: chuẩn hóa dữ liệu, phân loại tin World Cup, transform event, idempotency, reject quarantine.
- `tests/test_api.py`: health, OpenAPI, legacy/new statistics, advanced filtering, search, detail pages, news visibility và static frontend.
- `tests/conftest.py`: database SQLite cô lập và dataset chung kết 2022 tối thiểu.

MySQL vẫn phải được kiểm tra riêng vì SQLite không mô phỏng hoàn toàn collation, foreign key/index và DDL của MySQL.

## Chạy test

```powershell
python -m pytest tests -q
```

Kiểm tra schema ORM và migration không lệch nhau:

```powershell
python -m alembic current
python -m alembic heads
python -m alembic check
```

Kết quả mong đợi hiện tại:

```text
005_cleanup_demo_duplicates (head)
No new upgrade operations detected.
```

Kiểm tra MySQL read-only:

```powershell
python scripts/verify_mysql.py
```

Kiểm tra runtime:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/statistics/overview
Invoke-RestMethod http://127.0.0.1:8000/openapi.json
```

## Checklist trước khi bàn giao/deploy

- [ ] `pytest` vượt qua toàn bộ test.
- [ ] `alembic current` bằng `alembic heads`.
- [ ] `alembic check` không phát hiện operation mới.
- [ ] `/health` trả `200` và `database=connected`.
- [ ] Swagger mở được, không có route ngoài `/api/v1` trừ `/health`.
- [ ] Dashboard, list/detail, search, filter và pagination được smoke test.
- [ ] News API không trả bài `is_world_cup=false`.
- [ ] Không còn identifier demo cũ `2022-final`, `p-messi`, `p-mbappe` trong database.
- [ ] `.env` không được commit; password production đã thay.
- [ ] Backup MySQL đã tạo và restore thử trước migration production.
- [ ] Tài liệu API, frontend và feature matrix đã cập nhật nếu contract thay đổi.

## Regression cần ưu tiên

Khi thêm nguồn hoặc metric mới, tối thiểu phải có test cho:

1. Cùng payload chạy hai lần không tạo duplicate.
2. Payload lỗi đi vào `etl_rejects` nhưng job vẫn lưu bản ghi hợp lệ.
3. Filter `year/team/player/stage` thay đổi đúng tập kết quả.
4. Response Pydantic khớp OpenAPI.
5. Frontend xử lý được danh sách rỗng, lỗi 404/422/503 và ký tự HTML trong dữ liệu nguồn.
