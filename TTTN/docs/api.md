# REST API Reference

API ổn định sử dụng prefix `/api/v1`. Swagger UI tại `/docs`, ReDoc tại `/redoc` và schema máy đọc tại `/openapi.json` là nguồn tham chiếu cuối cùng khi code thay đổi.

## Quy ước chung

- Tất cả endpoint hiện tại là `GET` và trả JSON UTF-8.
- Danh sách dùng `limit` và `offset`; `limit` tối đa 100. Search giới hạn tối đa 25 kết quả cho mỗi nhóm.
- ID đội/cầu thủ/trận là khóa nội bộ MySQL. Năm World Cup dùng số bốn chữ số.
- Bộ lọc `stage` không phân biệt chữ hoa/thường; lấy giá trị đang có bằng `GET /api/v1/matches/stages`.
- Bàn luân lưu không cộng vào `home_score`, `away_score` hoặc tổng bàn thắng chính thức.
- Endpoint thống kê mới trả envelope `{ "data": ..., "meta": ... }`.
- `404` dùng khi tài nguyên không tồn tại; `422` dùng khi query parameter sai hoặc mâu thuẫn; `/health` trả `503` nếu database không sẵn sàng.

## Tournaments

| Endpoint | Chức năng |
|---|---|
| `GET /tournaments` | Danh sách các kỳ World Cup |
| `GET /tournaments/{year}` | Metadata một kỳ |
| `GET /tournaments/{year}/overview` | Tổng đội, trận, cầu thủ, bàn thắng và tin liên quan |
| `GET /tournaments/{year}/teams` | Đội tham dự, thứ hạng chung cuộc và huấn luyện viên nếu có |
| `GET /tournaments/{year}/standings?snapshot=final` | Bảng xếp hạng của snapshot |

## Teams, Players và Matches

| Endpoint | Query parameter |
|---|---|
| `GET /teams` | `q`, `limit`, `offset` |
| `GET /teams/{team_id}` | — |
| `GET /players` | `q`, `tournament_year`, `team_id`, `stage`, `limit`, `offset` |
| `GET /players/{player_id}` | — |
| `GET /matches` | `year` hoặc alias `tournament_year`, `team_id`, `player_id`, `stage`, `limit`, `offset` |
| `GET /matches/stages` | — |
| `GET /matches/{match_id}` | Trả thông tin trận và timeline sự kiện |

Không gửi đồng thời `year` và `tournament_year` với hai giá trị khác nhau. `matches/stages` phải được dùng để tạo dropdown nếu dữ liệu được nhập từ nguồn mới có cách đặt tên vòng đấu khác.

## News

| Endpoint | Query parameter |
|---|---|
| `GET /news` | `q`, `tournament_year`, `limit`, `offset` |
| `GET /news/{article_id}` | — |

News API chỉ trả bài có `news_articles.is_world_cup = true`. Bài bị bộ phân loại loại bỏ được giữ trong database để kiểm toán nhưng trả `404` ở endpoint chi tiết.

## Statistics API

| Endpoint | Metric |
|---|---|
| `GET /statistics/overview` | Tổng dữ liệu dashboard |
| `GET /statistics/tournaments/goals` | Bàn thắng theo kỳ |
| `GET /statistics/teams/titles` | Số chức vô địch |
| `GET /statistics/teams/tournaments` | Số kỳ tham dự |
| `GET /statistics/teams/goals` | Bàn thắng theo đội |
| `GET /statistics/teams/wins` | Trận thắng, gồm thắng luân lưu |
| `GET /statistics/players/goals` | Bàn thắng cá nhân, không tính phản lưới |
| `GET /statistics/players/matches` | Số trận ra sân |
| `GET /statistics/players/tournaments` | Số kỳ có tên trong đội hình |
| `GET /statistics/matches/goals` | Trận có tổng tỷ số cao nhất |
| `GET /statistics/matches/cards` | Trận nhiều thẻ; thêm `card_type=all|yellow|red` |

Các metric phù hợp hỗ trợ `year`, `team_id`, `player_id`, `stage`, `limit`. Ví dụ:

```http
GET /api/v1/statistics/players/goals?year=2022&team_id=1&stage=final&limit=10
```

Response chuẩn:

```json
{
  "data": [
    {"rank": 1, "player_id": 10, "player_name": "Example", "metric": "goals", "value": 8}
  ],
  "meta": {
    "metric": "goals",
    "count": 1,
    "filters": {"year": 2022, "stage": "final"}
  }
}
```

Các route `/api/v1/stats/*` là compatibility layer, đã được đánh dấu deprecated trong OpenAPI và không nên dùng cho client mới.

## Search

```http
GET /api/v1/search?q=Argentina&year=2022&team_id=1&stage=final&limit=8
```

Search trả năm nhóm: `tournaments`, `teams`, `players`, `matches`, `news`. Bộ lọc được áp dụng cho nhóm có quan hệ tương ứng:

- `year`: kỳ, đội tham dự kỳ đó, cầu thủ trong đội hình kỳ đó, trận và tin của kỳ đó.
- `team_id`: đội, cầu thủ thuộc đội và các trận của đội.
- `player_id`: cầu thủ và các trận có lượt ra sân của cầu thủ.
- `stage`: cầu thủ có lượt ra sân và trận thuộc vòng đấu.

`q` dài từ 2 đến 100 ký tự. Search là tìm chuỗi con bằng collation MySQL; hệ thống chưa cung cấp fuzzy search hoặc full-text ranking.

## Ví dụ gọi API

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/matches?year=2022&stage=final'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/statistics/teams/titles?limit=5'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/search?q=Messi&year=2022'
```

API chưa có authentication vì frontend và backend đang cùng một ứng dụng. Nếu public ra Internet, triển khai rate limit/API gateway và cơ chế xác thực phù hợp với đối tượng sử dụng.
