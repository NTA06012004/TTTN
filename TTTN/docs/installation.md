# Hướng dẫn cài đặt World Cup Data Platform

## 1. Yêu cầu hệ thống

- Python 3.11 trở lên; khuyến nghị Python 3.13.
- MySQL 8.0/8.4 hoặc Docker Desktop.
- Tối thiểu 2 GB RAM và khoảng 2 GB dung lượng trống.
- Kết nối Internet nếu chạy crawler/ETL.

Kiểm tra công cụ:

```powershell
python --version
docker --version
docker compose version
```

## 2. Cài đặt local trên Windows

### Bước 1 — Tạo môi trường Python

```powershell
cd C:\path\to\TTTN
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn activate script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### Bước 2 — Khởi động MySQL

Chỉ chạy MySQL bằng Docker, còn FastAPI chạy trên máy:

```powershell
docker compose up -d mysql
docker compose ps
```

MySQL Workbench có thể kết nối bằng:

```text
Host: 127.0.0.1
Port: 3306
User: worldcup
Password: worldcup
Database: worldcup
```

Tài khoản `root` dùng giá trị `MYSQL_ROOT_PASSWORD` trong `.env`. Không sử dụng mật khẩu mẫu ở production.

### Bước 3 — Cấu hình môi trường

```powershell
Copy-Item .env.example .env
```

Biến quan trọng:

| Biến | Ý nghĩa | Giá trị local |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `mysql+pymysql://worldcup:worldcup@127.0.0.1:3306/worldcup?charset=utf8mb4` |
| `CRAWLER_USER_AGENT` | Định danh crawler | Nên chứa email liên hệ thật |
| `REQUEST_TIMEOUT_SECONDS` | Timeout HTTP | `20` |
| `CRAWLER_DELAY_SECONDS` | Khoảng nghỉ giữa request | `1.0` |

Nếu mật khẩu có ký tự `@`, `:`, `/`, `#` hoặc `%`, phải URL-encode trước khi đưa vào `DATABASE_URL`.

### Bước 4 — Tạo schema

```powershell
python -m alembic upgrade head
python -m alembic current
```

Revision mong đợi:

```text
005_cleanup_demo_duplicates (head)
```

### Bước 5 — Nạp dữ liệu

Dữ liệu demo nhỏ:

```powershell
python -m app.cli seed-editions
python -m app.cli seed-demo
```

Toàn bộ dữ liệu lịch sử và tin tức:

```powershell
python -m app.cli seed-editions
python -m app.cli etl --all-years
```

ETL idempotent nên có thể chạy lại. Payload sai được ghi vào `etl_rejects` thay vì làm rollback toàn bộ nguồn.

`seed-demo` và ETL lịch sử dùng cùng external ID cho trận/cầu thủ mẫu, nên có thể chạy theo bất kỳ thứ tự nào mà không tạo bản sao demo.

### Bước 6 — Chạy ứng dụng

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Địa chỉ:

- Website: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

## 3. Chạy toàn bộ bằng Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
docker compose logs -f api
```

Nạp dữ liệu trong container:

```powershell
docker compose exec api python -m app.cli seed-editions
docker compose exec api python -m app.cli etl --all-years
```

Dừng hệ thống nhưng giữ database:

```powershell
docker compose down
```

Chỉ dùng `docker compose down -v` khi muốn xóa hoàn toàn volume MySQL và toàn bộ dữ liệu.

## 4. Kiểm thử

```powershell
python -m pytest tests -q
```

Kiểm tra API nhanh:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/statistics/overview
```

## 5. Lỗi thường gặp

### `Access denied for user`

- Kiểm tra user/password trong `.env` và `docker-compose.yml`.
- Nếu volume MySQL đã tồn tại, đổi biến môi trường không tự đổi mật khẩu trong database.
- Xác nhận đang kết nối đúng port và đúng tài khoản `worldcup` hoặc `root`.

### Port 3306 hoặc 8000 đã được sử dụng

```powershell
Get-NetTCPConnection -LocalPort 3306,8000 -ErrorAction SilentlyContinue
```

Đổi `APP_PORT` nếu port 8000 bị chiếm. Nếu MySQL local đã dùng 3306, dừng service đó hoặc đổi mapping port trong Compose và sửa `DATABASE_URL`.

### API chạy nhưng website không có dữ liệu

```powershell
python -m alembic current
python -m app.cli seed-editions
python -m app.cli etl --year 2022
```

### Migration không chạy

Đảm bảo `.env` tồn tại, MySQL healthy và `DATABASE_URL` có `charset=utf8mb4`. Xem log bằng:

```powershell
docker compose logs mysql
docker compose logs api
```
