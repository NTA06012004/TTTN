# Deployment Guide

Tài liệu này mô tả hai cách triển khai production: Docker Compose (khuyến nghị) và systemd. Kiến trúc chuẩn:

```text
Internet -> HTTPS/Nginx -> FastAPI/Uvicorn -> MySQL 8.4
                                  |
                           Scheduler ETL riêng
```

## 1. Chuẩn bị máy chủ

Khuyến nghị Ubuntu 24.04 LTS, 2 vCPU, 4 GB RAM, 20 GB SSD. Cài Docker Engine, Docker Compose plugin, Nginx và Certbot.

Firewall chỉ mở:

- `22/tcp` cho SSH, giới hạn IP quản trị nếu có thể.
- `80/tcp` và `443/tcp` cho website.
- Không public port MySQL `3306` trên production.

## 2. Triển khai bằng Docker Compose

### Bước 1 — Chuẩn bị source và secret

```bash
sudo mkdir -p /opt/worldcup
sudo chown "$USER":"$USER" /opt/worldcup
cd /opt/worldcup
git clone <repository-url> .
cp .env.example .env
chmod 600 .env
```

Thay ít nhất các giá trị sau bằng chuỗi mạnh, không commit `.env`:

```dotenv
MYSQL_DATABASE=worldcup
MYSQL_USER=worldcup_app
MYSQL_PASSWORD=<strong-random-password>
MYSQL_ROOT_PASSWORD=<different-strong-random-password>
APP_PORT=8000
APP_BIND=127.0.0.1
UVICORN_WORKERS=2
CRAWLER_USER_AGENT=WorldCupResearchBot/1.0 (+mailto:admin@example.com)
```

Nếu mật khẩu chứa ký tự đặc biệt dành riêng cho URL, URL-encode hoặc đặt `DATABASE_URL` rõ ràng khi chạy app ngoài Compose.

### Bước 2 — Build và khởi động

```bash
docker compose build --pull api
docker compose up -d
docker compose ps
docker compose logs --tail=100 api
```

Service `api` chờ MySQL healthy, chạy `alembic upgrade head`, sau đó mới khởi động Uvicorn.

### Bước 3 — Seed và ETL lần đầu

```bash
docker compose exec api python -m app.cli seed-editions
docker compose exec api python -m app.cli etl --all-years
```

Không chạy ETL đồng thời ở nhiều container vì có thể tăng tải nguồn và database không cần thiết.

### Bước 4 — Kiểm tra

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/api/v1/statistics/overview
docker compose ps
```

Health check chỉ trả `200` khi cả FastAPI và kết nối MySQL hoạt động.

## 3. Nginx và HTTPS

Sao chép cấu hình mẫu và thay domain:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/worldcup
sudo sed -i 's/worldcup.example.com/your-domain.example/g' /etc/nginx/sites-available/worldcup
sudo ln -s /etc/nginx/sites-available/worldcup /etc/nginx/sites-enabled/worldcup
sudo nginx -t
sudo systemctl reload nginx
```

Cấp chứng chỉ TLS:

```bash
sudo certbot --nginx -d your-domain.example
sudo certbot renew --dry-run
```

Compose mặc định chỉ bind API và MySQL vào `127.0.0.1`; Nginx trên cùng máy chủ là điểm truy cập public duy nhất. Không đổi `APP_BIND` thành `0.0.0.0` nếu firewall chưa được cấu hình.

## 4. Lập lịch ETL

Ví dụ cron chạy lúc 02:15 Chủ nhật, dùng `flock` để ngăn hai job chạy cùng lúc:

```cron
15 2 * * 0 cd /opt/worldcup && /usr/bin/flock -n /tmp/worldcup-etl.lock /usr/bin/docker compose exec -T api python -m app.cli etl --all-years >> /var/log/worldcup-etl.log 2>&1
```

Tin mới có thể chạy hằng giờ bằng `crawl-news`; dữ liệu lịch sử chỉ cần chạy lại định kỳ hoặc khi nguồn cập nhật.

## 5. Cập nhật phiên bản

```bash
cd /opt/worldcup
git pull --ff-only
docker compose build api
docker compose up -d api
docker compose exec api python -m alembic current
curl --fail http://127.0.0.1:8000/health
```

Luôn backup database trước migration. Không dùng `git reset --hard` trên server có thay đổi cấu hình chưa lưu.

## 6. Backup và khôi phục MySQL

Backup:

```bash
mkdir -p /opt/backups/worldcup
docker compose exec -T mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers "$MYSQL_DATABASE"' | gzip > /opt/backups/worldcup/worldcup-$(date +%F-%H%M).sql.gz
```

Khôi phục vào database trống:

```bash
gunzip -c /opt/backups/worldcup/worldcup-YYYY-MM-DD-HHMM.sql.gz | docker compose exec -T mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
```

Định kỳ thử khôi phục trên môi trường staging; một file backup chưa từng restore không được xem là backup đã xác minh.

## 7. Triển khai không dùng Docker

```bash
sudo useradd --system --home /opt/worldcup --shell /usr/sbin/nologin worldcup
sudo mkdir -p /opt/worldcup
sudo chown worldcup:worldcup /opt/worldcup
sudo -u worldcup python3 -m venv /opt/worldcup/.venv
sudo -u worldcup /opt/worldcup/.venv/bin/python -m pip install -r /opt/worldcup/requirements.txt
sudo cp deploy/worldcup.service /etc/systemd/system/worldcup.service
sudo systemctl daemon-reload
sudo systemctl enable --now worldcup
```

Đặt file `/opt/worldcup/.env` với quyền `600`, đảm bảo MySQL đã sẵn sàng trước khi start service.

## 8. Monitoring và vận hành

- Uptime monitor: `GET /health` mỗi 30–60 giây.
- Theo dõi HTTP 5xx, latency p95, CPU/RAM và dung lượng volume MySQL.
- Theo dõi `crawl_runs.status`, `records_rejected` và bảng `etl_rejects`.
- Giữ log ứng dụng/ETL có rotation; không ghi password hoặc raw secret vào log.
- Thiết lập cảnh báo khi health check lỗi liên tiếp hoặc backup không được tạo đúng lịch.

## 9. Security checklist

- Thay toàn bộ password mẫu và không commit `.env`.
- Không public port `3306`.
- Bật HTTPS và tự động gia hạn certificate.
- Chỉ cấp quyền database cần thiết cho user ứng dụng.
- Cập nhật image/Python dependency định kỳ và chạy test trước deploy.
- Thêm rate limiting hoặc API gateway nếu mở API công khai.
- Chỉ crawler các nguồn phù hợp robots.txt, điều khoản sử dụng và bản quyền.

## 10. Rollback

1. Giữ image/tag phiên bản trước khi update.
2. Nếu code mới lỗi nhưng schema vẫn tương thích, chạy lại image cũ.
3. Chỉ downgrade Alembic sau khi đã đọc migration và có backup xác minh.
4. Nếu migration làm thay đổi dữ liệu không thể đảo ngược, restore backup thay vì downgrade mù quáng.

Migration `005_cleanup_demo_duplicates` là data cleanup một chiều: downgrade không tái tạo các identifier demo đã hợp nhất. Nếu cần khôi phục trạng thái trước migration này, phải dùng backup.
