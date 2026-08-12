# Nguồn dữ liệu và phạm vi sử dụng

Hệ thống tách nguồn cấu trúc, nguồn mô tả và nguồn tin tức. Mỗi adapter lưu nguồn, checksum và payload chuẩn hóa trong `data_provenance`; việc có adapter kỹ thuật không thay thế nghĩa vụ kiểm tra giấy phép và điều khoản sử dụng trước khi vận hành production.

## Nguồn đang tích hợp

| Nguồn | Adapter/command | Dữ liệu | Phạm vi |
|---|---|---|---|
| [Fjelstul World Cup Database](https://github.com/jfjelstul/worldcup) | `etl`, `crawl-source fjelstul_*` | Trận, đội hình, lượt ra sân, bảng xếp hạng, bàn, thẻ, luân lưu, thay người | World Cup nam 1930–2022, CC BY-SA 4.0 |
| [Wikipedia MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page) | `wikipedia_editions` | Tóm tắt từng kỳ | Theo năm, có attribution nguồn |
| [International football results](https://github.com/martj42/international_results) | `international_results` | Kết quả trận được lọc chính xác `tournament = FIFA World Cup` | Adapter bổ sung, không nằm trong orchestration `etl` mặc định |
| RSS báo Việt Nam | `crawl-news` | Tiêu đề, tóm tắt, ngày, URL, nguồn | Tin mới từ sáu tòa soạn cấu hình trong `news.py` |
| Google News RSS search | `crawl-news --year YEAR` | Metadata kho bài cũ | Chỉ các domain báo Việt Nam được cấu hình |
| Seed metadata | `seed-editions` | Năm, chủ nhà, vô địch, á quân | 23 kỳ 1930–2026 |

Kết quả 2026 trong seed hiện khớp bảng xếp hạng chung cuộc do [FIFA công bố](https://www.fifa.com/en/articles/final-tournament-standings). Dataset Fjelstul hiện chỉ cung cấp dữ liệu cấu trúc đến 2022, nên seed 2026 không tự tạo trận, cầu thủ hoặc sự kiện 2026.

## Phạm vi lưu tin tức

World Cup Atlas chỉ lưu metadata và link về tòa soạn; không sao chép toàn văn. Bộ phân loại yêu cầu ngữ cảnh FIFA World Cup bóng đá nam cấp đội tuyển và loại:

- FIFA Club World Cup/câu lạc bộ;
- World Cup nữ, futsal, bóng đá bãi biển và giải U17/U20;
- World Cup của bóng chuyền, billiards, cờ vua, rugby, cricket, bóng rổ, eSports và các môn khác.

Bài không phù hợp mang `is_world_cup=false`, không xuất hiện ở API/frontend nhưng vẫn được giữ để kiểm tra và phân loại lại bằng `python -m app.cli reclassify-news`.

## Quy tắc vận hành nguồn

1. Cấu hình User-Agent có thông tin liên hệ thật.
2. Giữ delay giữa request, retry/backoff và tôn trọng `Retry-After`.
3. Kiểm tra robots.txt, điều khoản dịch vụ, bản quyền và attribution của từng nguồn.
4. Không chạy đồng thời cùng một job `source + year`.
5. Theo dõi `crawl_runs`, tỷ lệ reject và thay đổi schema nguồn.
6. Khi nguồn đổi identifier, viết migration/merge rõ ràng thay vì tạo entity mới theo tên hiển thị.

## Attribution khi công bố

Nếu phát hành dataset dẫn xuất có dữ liệu Fjelstul, giữ attribution và tuân thủ CC BY-SA 4.0. Với Wikipedia và báo chí, giữ URL nguồn trong từng provenance/article. Repo ứng dụng chưa tuyên bố một giấy phép chung cho toàn bộ code và dữ liệu; cần bổ sung `LICENSE` phù hợp trước khi phân phối công khai.
