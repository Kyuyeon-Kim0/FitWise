import json
import sqlite3
from pathlib import Path

from contextlib import contextmanager

from app.config import get_settings


@contextmanager
def connect(database=None):
    path = Path(database) if database is not None else get_settings().database
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def initialize(database=None, seed=True):
    with connect(database) as connection:
        # 다른 개발 작업의 기존 DB를 자동 변경하지 않습니다.
        expected = {
            "users": {"id", "name", "preferred_fit"},
            "products": {"id", "subcategory", "sizes", "measurements"},
            "orders": {"id", "user_id", "product_id", "size", "ordered_at"},
            "returns": {"id", "order_id", "reason", "returned_at"},
            "reviews": {"id", "user_id", "product_id", "size", "rating", "content", "created_at"},
            "agent_logs": {"id", "request_id", "agent_type", "processing_ms", "result_json", "status"},
            "resource_logs": {"id", "request_id", "operation", "memory_after_mb", "response_ms", "status"},
        }
        for table, required in expected.items():
            columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
            if columns and not required.issubset(columns):
                raise ValueError(f"기존 DB의 {table} 구조가 다릅니다. 원본을 보존하고 FITWISE_DB_PATH에 별도 경로를 지정하세요.")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        # 동시 세션에서도 샘플이 중복 생성되지 않도록 확인과 삽입을 묶습니다.
        connection.execute("BEGIN IMMEDIATE")
        if seed and not any(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            for table in ("products", "users", "orders", "reviews", "agent_logs", "resource_logs")):
            seed_demo(connection)
        connection.commit()


def seed_demo(connection):
    catalog = [
        ("에센셜 코튼 셔츠", "상의", "셔츠", 49000, "매일 손이 가는 부드러운 코튼. 여유로운 실루엣의 데일리 셔츠입니다.", "sage"),
        ("위켄드 라이트 자켓", "아우터", "자켓", 89000, "가벼운 외출에 어울리는 편안한 자켓. 이너를 겹쳐 입기 좋은 핏입니다.", "sand"),
        ("스트레이트 데님", "하의", "청바지", 69000, "자연스럽게 떨어지는 스트레이트 라인. 탄탄한 데님으로 오래 입으세요.", "blue"),
        ("소프트 라운드 니트", "상의", "니트", 59000, "차분한 컬러와 포근한 터치. 일상에 편안함을 더하는 기본 니트입니다.", "rose"),
        ("데일리 테일러드 코트", "아우터", "코트", 149000, "깔끔한 어깨선과 넉넉한 품의 조화. 간절기에 어울리는 코트입니다.", "stone"),
        ("릴랙스 와이드 슬랙스", "하의", "슬랙스", 65000, "여유로운 허벅지와 긴 기장. 움직임이 편안한 와이드 슬랙스입니다.", "ink"),
    ]
    comments = [
        (5, "정사이즈이고 착용감이 좋아요. 디자인도 예뻐요."),
        (4, "가벼워서 편안해요. 핏이 예뻐요."),
        (2, "사이즈가 커요. 소매가 길어요."),
        (5, "마감이 좋아요. 착용감이 편안해요."),
        (3, "소재가 얇아요. 디자인은 좋아요."),
        (4, "정사이즈라 잘 맞아요. 핏이 좋아요."),
        (2, "사이즈가 작아요. 조금 타이트해요."),
        (5, "가볍고 부드러워요. 디자인이 예뻐요."),
    ]
    with connection:
        connection.executemany("INSERT INTO users VALUES (?,?,?)", [
            (1, "김하늘", "레귤러"), (2, "이서준", "루즈"), (3, "박지우", "레귤러")])
        for pid, item in enumerate(catalog, 1):
            measurements = {}
            for i, size in enumerate(("S", "M", "L")):
                measurements[size] = ({"허리": 36 + i * 2, "허벅지": 29 + i * 2, "총장": 99 + i * 2}
                                      if item[1] == "하의" else
                                      {"어깨": 43 + i * 2, "가슴": 52 + i * 3,
                                       "총장": (85 if item[2] == "코트" else 66) + i * 2, "소매": 59 + i})
            connection.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?)", (
                pid, *item, json.dumps(["S", "M", "L"]), json.dumps(measurements, ensure_ascii=False)))
            for j in range(24):
                uid = j % 3 + 1
                size = ("S", "M", "L")[(j // 3 + pid) % 3]
                cursor = connection.execute(
                    "INSERT INTO orders(user_id,product_id,size,ordered_at) VALUES (?,?,?,?)",
                    (uid, pid, size, f"2026-08-{j + 1:02d}"))
                if (j + pid) % 5 == 0 or (uid == 1 and size == "L" and j % 2 == 0):
                    connection.execute("INSERT INTO returns(order_id,reason,returned_at) VALUES (?,?,?)",
                                       (cursor.lastrowid, "사이즈 큼" if size == "L" else "핏 불일치", "2026-08-28"))
            for j, (rating, content) in enumerate(comments):
                if item[1] == "하의":
                    content = content.replace("소매가 길어요", "기장이 길어요")
                connection.execute(
                    "INSERT INTO reviews(user_id,product_id,size,rating,content,created_at) VALUES (?,?,?,?,?,?)",
                    (j % 3 + 1, pid, ("S", "M", "L")[j % 3], rating, content, f"2026-08-{j + 10:02d}"))


if __name__ == "__main__":
    initialize()
    print("DB 준비 완료. 기존 데이터는 유지했습니다.")
