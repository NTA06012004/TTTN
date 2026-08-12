from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import router
from app.database import get_db
from app.schemas import HealthResponse


DESCRIPTION = """
World Cup Data REST API cung cấp dữ liệu lịch sử FIFA World Cup từ 1930 đến nay.

### Khả năng chính

* Tra cứu kỳ World Cup, đội tuyển, cầu thủ, trận đấu, bảng xếp hạng và tin tức.
* Statistics API với bộ lọc `year`, `team_id`, `player_id`, `stage` và `limit`.
* Search API tìm đồng thời đội tuyển, cầu thủ, trận đấu và kỳ World Cup.
* Các response thống kê dùng envelope thống nhất gồm `data` và `meta`.

### Quy ước

* API ổn định nằm dưới `/api/v1`.
* `limit` được giới hạn tối đa 100; danh sách lớn dùng thêm `offset`.
* Bàn luân lưu không được cộng vào tỷ số trận hoặc tổng bàn thắng chính thức.
* Các route `/api/v1/stats/*` được giữ để tương thích và đã đánh dấu deprecated.
"""

TAGS = [
    {"name": "System", "description": "Health/readiness endpoint phục vụ monitoring và deployment."},
    {"name": "Tournaments", "description": "Kỳ World Cup, tổng quan, đội tham dự và bảng xếp hạng."},
    {"name": "Teams", "description": "Danh sách và hồ sơ đội tuyển quốc gia."},
    {"name": "Players", "description": "Danh sách, bộ lọc và hồ sơ cầu thủ."},
    {"name": "Matches", "description": "Trận đấu và các sự kiện chi tiết trong trận."},
    {"name": "News", "description": "Metadata tin tức World Cup từ các báo Việt Nam."},
    {"name": "Statistics", "description": "API tổng hợp và xếp hạng, response chuẩn `data/meta`."},
    {"name": "Search", "description": "Tìm kiếm toàn cục trên nhiều loại tài nguyên."},
    {"name": "Legacy Statistics", "description": "Route cũ chỉ dùng cho client chưa chuyển sang `/statistics/*`."},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    # DDL được quản lý bằng Alembic, không tự thay đổi schema khi web worker khởi động.
    yield


app = FastAPI(
    title="World Cup Data REST API",
    version="2.0.0",
    summary="Tra cứu và thống kê lịch sử FIFA World Cup",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"displayRequestDuration": True, "filter": True, "persistAuthorization": True},
    contact={"name": "World Cup Data Platform"},
    license_info={"name": "Dataset attribution: CC BY-SA 4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/"},
    lifespan=lifespan,
)
app.include_router(router)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def website():
    return FileResponse(static_dir / "index.html")


@app.get("/health", response_model=HealthResponse, tags=["System"], summary="Kiểm tra API và MySQL")
def health(db: Annotated[Session, Depends(get_db)]):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ok", "version": app.version, "database": "connected"}
