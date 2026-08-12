# Ma trận truy vết chức năng

Tài liệu này là điểm đối chiếu nhanh giữa yêu cầu sản phẩm, giao diện, REST API, bảng MySQL và test. Khi thay đổi một cột trong cùng hàng, cần kiểm tra các cột còn lại.

| Chức năng | Frontend | REST API | Bảng/logic chính | Test |
|---|---|---|---|---|
| Dashboard tổng quan | `#/dashboard` | `/statistics/overview` | tournaments, teams, players, matches, events, news | `test_frontend_detail_and_visualization_endpoints` |
| Biểu đồ vô địch/bàn thắng | Dashboard | `/statistics/teams/*`, `/statistics/tournaments/goals` | aggregate trong `services.py` | `test_rest_team_statistics` |
| Danh sách/chi tiết kỳ | `#/world-cups*` | `/tournaments*` | tournaments, tournament_teams, standings | `test_new_edition_routes_and_frontend` |
| Danh sách/chi tiết đội | `#/teams*` | `/teams*`, team statistics | teams, tournament_teams, matches/events | `test_rest_team_statistics` |
| Danh sách/chi tiết cầu thủ | `#/players*` | `/players*`, player statistics | players, squads, appearances, events | `test_rest_player_statistics_and_filters` |
| Danh sách/chi tiết trận | `#/matches*` | `/matches*`, `/matches/stages` | matches, teams, match_events | `test_rest_match_statistics_and_advanced_search` |
| Bảng xếp hạng | `#/standings` | `/tournaments/{year}/standings` | standings | `test_new_edition_routes_and_frontend` |
| Tin World Cup | `#/news*` | `/news*` | news_articles + relevance classifier | `test_news_api_only_exposes_world_cup_articles` |
| Search toàn cục | Search dialog | `/search` | tournaments, teams, players, matches, news | `test_rest_match_statistics_and_advanced_search` |
| ETL idempotent | CLI | — | data_sources, crawl_runs, provenance | `test_etl_is_idempotent` |
| Quarantine dữ liệu lỗi | CLI | — | etl_rejects | `test_invalid_record_is_quarantined` |
| Swagger/OpenAPI | `/docs`, `/redoc` | `/openapi.json` | FastAPI schemas/tags | `test_openapi_documentation` |
| Health/readiness | — | `/health` | `SELECT 1` MySQL | `test_health` |

## Contract cần giữ ổn định

- Frontend chỉ gọi endpoint qua registry trong `app/static/js/api.js`.
- Statistics response luôn có `data` và `meta`.
- News chỉ hiển thị `is_world_cup=true` ở list, detail, search và dashboard count.
- `year` là tên chuẩn cho statistics/search; resource players/news vẫn dùng `tournament_year`; matches chấp nhận cả hai để tương thích.
- Vòng đấu hiển thị theo giá trị database nhưng filter không phân biệt chữ hoa/thường.
- Legacy `/stats/*` chỉ được sửa để duy trì tương thích, không thêm chức năng mới.
