# Frontend Architecture

Frontend là SPA không cần bước build, dùng ES Modules và hash routing. FastAPI phục vụ toàn bộ file trong `app/static`, vì vậy frontend gọi REST API cùng origin và không cần CORS trong cấu hình mặc định.

## Cấu trúc

```text
app/static/
├── index.html          App shell: sidebar, topbar, search dialog, footer
├── styles.css          Design tokens, component styles, responsive breakpoints
├── app.js              Router setup, global loading/error state, global search
└── js/
    ├── api.js          HTTP client và endpoint registry
    ├── router.js       Hash router và query-string state
    ├── components.js   Card, chart, form, pagination, loading/empty/error state
    └── pages.js        Page controllers và HTML composition
```

Luồng render:

```text
URL hash -> Router -> page controller -> Promise.all REST calls
         -> skeleton -> component HTML -> mount form handlers
         -> empty state hoặc error/retry nếu cần
```

`activeRender` trong `app.js` ngăn response của route cũ ghi đè route mới khi người dùng chuyển trang nhanh.

## Route và dependency API

| Frontend route | API chính |
|---|---|
| `#/dashboard` | overview và toàn bộ Statistics API phục vụ biểu đồ |
| `#/world-cups` | `/tournaments` |
| `#/world-cups/{year}` | tournament detail/overview/teams/standings, matches, news |
| `#/teams` | `/teams`, `/tournaments/{year}/teams` |
| `#/teams/{id}` | team detail, team statistics, matches, players |
| `#/players` | `/players` với năm/đội/phân trang |
| `#/players/{id}` | player detail, player statistics, matches |
| `#/matches` | `/matches`, `/matches/stages` |
| `#/matches/{id}` | match detail và timeline events |
| `#/standings` | tournament list và standings theo năm |
| `#/news` | `/news` với tìm kiếm/năm/phân trang |
| `#/news/{id}` | news detail metadata và liên kết tòa soạn |

Global search gọi `/search` sau debounce 260 ms và render đội, cầu thủ, trận, kỳ World Cup cùng tin tức.

## State và component

- Filter nằm trong query string của hash URL nên có thể bookmark/chia sẻ.
- Lookup kỳ đấu, đội và vòng đấu được cache trong bộ nhớ cho phiên đang mở.
- Pagination dùng `limit/offset`; nút sau bị khóa khi trang hiện tại trả ít hơn page size.
- Nội dung lấy từ API luôn qua `escapeHtml`. Link bài báo chỉ chấp nhận protocol `http` hoặc `https`.
- Skeleton xuất hiện trước khi request hoàn tất; danh sách rỗng dùng empty state; lỗi HTTP dùng error state có nút retry.
- CSS có breakpoint 1180, 900 và 640 px, đồng thời tôn trọng `prefers-reduced-motion`.

## Thêm trang hoặc endpoint

1. Khai báo REST call trong `js/api.js`.
2. Tạo page controller trong `js/pages.js`, tái sử dụng component hiện có.
3. Đăng ký route và metadata trong `app.js`.
4. Thêm navigation nếu đây là trang cấp cao.
5. Bổ sung test kiểm tra static asset và API dependency.
6. Cập nhật `docs/feature-matrix.md` và tài liệu API nếu có route backend mới.

Frontend hiện không dùng framework hoặc bundler. Nếu chuyển sang React/Vue/Vite, cần giữ nguyên contract `/api/v1`, route deep-link và các trạng thái loading/empty/error trước khi thay kiến trúc triển khai.
