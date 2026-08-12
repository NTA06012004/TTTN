# World Cup Data Platform (Python)

Hệ thống gồm ba phần: MySQL để lưu dữ liệu, crawler có thể mở rộng theo nguồn, và FastAPI cung cấp API thống kê.

| Thành phần | Công nghệ |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2 |
| Database | MySQL 8.4, Alembic |
| ETL | Requests, RSS/CSV/MediaWiki adapters |
| Frontend | ES Modules, component-based SPA, responsive CSS |
| Deployment | Docker Compose, Uvicorn, Nginx |

Tài liệu:

- [Cài đặt local và Docker](docs/installation.md)
- [Deployment Guide](docs/deployment.md)
- [Thiết kế database và ETL](docs/database.md)
- [REST API Reference](docs/api.md)
- [Frontend Architecture](docs/frontend.md)
- [Nguồn dữ liệu và phạm vi sử dụng](docs/data-sources.md)
- [Testing và Release Checklist](docs/testing.md)
- [Ma trận truy vết chức năng](docs/feature-matrix.md)
- Swagger UI: `/docs`, ReDoc: `/redoc`, OpenAPI JSON: `/openapi.json`

## 1. Kiến trúc

```text
CSV/RSS/MediaWiki -> Extract -> làm sạch + chuẩn hóa + kiểm tra
                                      |
                       provenance + SHA-256 chống trùng
                                      |
                      MySQL nghiệp vụ / etl_rejects
                                      |
                              FastAPI /api/v1/*
```

Các bảng chính:

- `tournaments`: từng kỳ World Cup, nước chủ nhà, nhà vô địch.
- `teams`, `players`: đội tuyển và cầu thủ (không lặp giữa các kỳ).
- `squads`: cầu thủ thuộc đội nào ở kỳ nào.
- `matches`: lịch đấu, tỷ số và trạng thái.
- `appearances`: số phút/trận của cầu thủ.
- `match_events`: bàn thắng, thẻ vàng/đỏ, phản lưới, penalty.
- `standings`: lịch sử bảng xếp hạng theo vòng/kỳ.
- `news_articles`: bài báo Việt Nam, URL là khóa chống trùng.

## 2. Chạy nhanh với MySQL

Yêu cầu Python 3.11+:

```powershell
docker compose up -d mysql
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.cli seed-editions
python -m app.cli seed-demo
uvicorn app.main:app --reload
```

Mở website tại `http://127.0.0.1:8000` và tài liệu API tại `http://127.0.0.1:8000/docs`. Production thay toàn bộ mật khẩu mặc định trong `.env` và `docker-compose.yml`.

Chạy cả MySQL và API bằng container:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose exec api python -m app.cli seed-editions
```

## 3. Thu thập dữ liệu

Chạy ETL đầy đủ cho một kỳ hoặc toàn bộ lịch sử:

```powershell
python -m app.cli etl --year 2022
python -m app.cli etl --all-years
```

Có thể bỏ qua nguồn tin hoặc metadata khi chỉ cần dữ liệu bóng đá có cấu trúc:

```powershell
python -m app.cli etl --all-years --skip-news --skip-wikipedia
```

ETL cấu trúc sử dụng [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup) (CC BY-SA 4.0), gồm trận đấu, bảng xếp hạng vòng bảng/chung cuộc, đội hình, lượt ra sân, bàn thắng, thẻ phạt, luân lưu và thay người từ 1930–2022. Metadata kỳ 2026 được seed riêng; dữ liệu trận/sự kiện 2026 chỉ xuất hiện khi có nguồn cấu trúc tương ứng. Tin tiếng Việt được lấy dưới dạng metadata từ RSS/kho tìm kiếm của VnExpress, Tuổi Trẻ, Thanh Niên, VietnamNet, Dân Trí và Lao Động.

Các HTTP adapter dùng chung retry/backoff; từng bản ghi được kiểm tra độc lập. Bản ghi sai được lưu vào `etl_rejects`, còn bản hợp lệ vẫn được commit. Khóa `(source_id, entity_type, external_key)` cùng SHA-256 nội dung giúp chạy lại an toàn: dữ liệu không đổi có `saved=0`, dữ liệu đổi được cập nhật.

Thu thập RSS báo Việt Nam (lọc bài có từ khóa World Cup):

```powershell
python -m app.cli crawl-news
python -m app.cli crawl-news --year 1998
```

Crawler chỉ lưu tin có cụm `World Cup`/`Cúp thế giới` liên quan đến giải bóng đá nam cấp đội tuyển. Club World Cup, World Cup nữ, futsal, giải trẻ và World Cup của môn khác được loại ngay ở bước transform. Phân loại lại dữ liệu tin cũ sau khi thay đổi quy tắc bằng:

```bash
python -m app.cli reclassify-news
```

Tin không phù hợp được giữ trong database với `is_world_cup = false` để kiểm tra nguồn, nhưng không xuất hiện ở News API, Search API, dashboard hoặc frontend.

Thu thập metadata từng kỳ từ MediaWiki và trận lịch sử từ bộ dữ liệu mở:

```powershell
python -m app.cli crawl-source wikipedia_editions --year 1998
python -m app.cli crawl-source international_results --year 1998
```

Nhập dữ liệu lịch sử từ JSON chuẩn hóa:

```powershell
python -m app.cli import-json data/example_world_cup.json
```

JSON importer dùng transaction và upsert, vì vậy có thể chạy lại an toàn. Mẫu tại `data/example_world_cup.json` dùng cùng external ID với dataset cấu trúc để không tạo bản sao cầu thủ/trận. Khi bổ sung nguồn mới, tạo `CrawlerAdapter` trả `SourceRecord` với payload chuẩn hóa; `app/schemas.py` chỉ dành cho response API.

## 4. API chính

- `GET /api/v1/tournaments`
- `GET /api/v1/tournaments/{year}`
- `GET /api/v1/tournaments/{year}/overview`
- `GET /api/v1/tournaments/{year}/teams`
- `GET /api/v1/tournaments/{year}/standings`
- `GET /api/v1/teams`, `GET /api/v1/players`
- `GET /api/v1/matches?tournament_year=2022&team_id=...`
- `GET /api/v1/matches/stages`
- `GET /api/v1/news?q=World%20Cup&limit=20`
- `GET /api/v1/stats/teams/most-titles`
- `GET /api/v1/stats/players/top-scorers`
- `GET /api/v1/stats/players/most-appearances`
- `GET /api/v1/stats/matches/most-goals`
- `GET /api/v1/stats/matches/most-cards`
- `GET /api/v1/search?q=...`

Tham số `limit` luôn bị giới hạn để tránh truy vấn quá lớn. Statistics và Search dùng `year`; danh sách cầu thủ/tin dùng `tournament_year`; danh sách trận chấp nhận cả hai tên để tương thích.

### Statistics REST API v2

Các route mới trả cùng một envelope:

```json
{
  "data": [{"rank": 1, "metric": "goals", "value": 16}],
  "meta": {"metric": "goals", "count": 1, "filters": {"year": 2022}}
}
```

- `GET /api/v1/statistics/teams/titles`
- `GET /api/v1/statistics/teams/tournaments`
- `GET /api/v1/statistics/teams/goals`
- `GET /api/v1/statistics/teams/wins`
- `GET /api/v1/statistics/players/goals`
- `GET /api/v1/statistics/players/matches`
- `GET /api/v1/statistics/players/tournaments`
- `GET /api/v1/statistics/matches/goals`
- `GET /api/v1/statistics/matches/cards?card_type=all|yellow|red`

Advanced Filtering dùng các query parameter `year`, `team_id`, `player_id`, `stage` và `limit` ở những resource phù hợp. `stage` không phân biệt chữ hoa/thường và frontend lấy danh sách vòng đấu động từ `/matches/stages`. `GET /api/v1/matches` hỗ trợ thêm `offset`; tên cũ `tournament_year` vẫn được giữ để tương thích. Search API trả đủ kỳ đấu, đội, cầu thủ, trận và tin tức:

```text
GET /api/v1/search?q=Brazil&year=2022&stage=quarter-finals
```

Các route `/api/v1/stats/*` cũ vẫn hoạt động như compatibility layer. Danh mục endpoint và quy tắc filter đầy đủ nằm trong [docs/api.md](docs/api.md); OpenAPI/Swagger tại `http://127.0.0.1:8000/docs`.

## 5. Frontend Architecture

Frontend là SPA component-based dùng ES Modules và hash routing, được FastAPI phục vụ cùng origin nên không cần cấu hình CORS:

```text
app/static/
├── index.html          # App shell: sidebar, header, search dialog, footer
├── styles.css          # Design system và responsive layout
├── app.js              # Khởi tạo router, layout state và global search
└── js/
    ├── api.js          # REST client và endpoint registry
    ├── router.js       # Hash router và query-string
    ├── components.js   # Card, chart, filter, pagination, UI states
    └── pages.js        # Dashboard và các trang list/detail
```

Các route giao diện:

- `#/dashboard`
- `#/world-cups`, `#/world-cups/{year}`
- `#/teams`, `#/teams/{id}`
- `#/players`, `#/players/{id}`
- `#/matches`, `#/matches/{id}`
- `#/standings?year=2022`
- `#/news`, `#/news/{id}`

Dashboard lấy dữ liệu từ Statistics REST API và hiển thị biểu đồ số danh hiệu, bàn thắng theo đội và phân bố bàn thắng theo năm. Các danh sách hỗ trợ filter/pagination bằng URL, nhờ vậy có thể bookmark hoặc chia sẻ trạng thái đang xem. Mọi trang đều có skeleton loading, empty state và error/retry state.

## 6. Triển khai

Image ứng dụng chạy bằng user không đặc quyền; Compose chờ MySQL healthy, tự áp dụng Alembic và mới khởi động Uvicorn. Cấu hình Nginx/systemd mẫu nằm trong `deploy/`.

Quy trình production, HTTPS, ETL scheduler, backup/restore, monitoring, security và rollback được mô tả tại [docs/deployment.md](docs/deployment.md).

## 7. Kiểm thử

```powershell
python -m pytest tests -q
```

Thiết kế chi tiết và ERD: [docs/database.md](docs/database.md).

## Lưu ý production

- Kiểm tra `robots.txt`, điều khoản sử dụng và bản quyền của từng nguồn trước khi crawl; RSS chỉ lưu metadata và liên kết, không sao chép toàn bài.
- Chạy crawler bằng scheduler/queue, thêm retry + backoff và cache HTTP; không tăng tần suất tùy tiện.
- Dùng MySQL replica/backup, Alembic, secret manager, rate-limit/auth cho API, log/monitoring và backup định kỳ.
- Kết quả penalty shoot-out không cộng vào `home_score`/`away_score`; bàn phản lưới được ghi bằng event `own_goal` để truy vấn chính xác.
