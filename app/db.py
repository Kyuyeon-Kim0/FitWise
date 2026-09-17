import json
import random
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
            "users": {"id", "name", "preferred_fit", "height"},
            "products": {"id", "subcategory", "sizes", "measurements"},
            "orders": {"id", "user_id", "product_id", "size", "ordered_at"},
            "returns": {"id", "order_id", "reason", "returned_at"},
            "reviews": {"id", "user_id", "product_id", "size", "rating", "content", "created_at"},
            "review_analysis": {"id", "product_id", "result_json", "created_at"},
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
        # 상의 추가
        ("베이직 코튼 티셔츠", "상의", "티셔츠", 29000, "FitBasic의 사계절 데일리 티셔츠. 면 100% 소재로 부드럽고 편안한 레귤러핏입니다.", "sand"),
        ("오버핏 스트라이프 셔츠", "상의", "셔츠", 49000, "UrbanLine의 봄가을 셔츠. 면 70%·폴리 30% 혼방의 여유로운 오버핏입니다.", "blue"),
        ("크루넥 스웨트셔츠", "상의", "맨투맨", 45000, "WarmMood의 가을겨울 맨투맨. 기모 안감으로 따뜻하고 레귤러핏으로 데일리에 좋습니다.", "stone"),
        ("후드 집업", "상의", "후드", 58000, "ActiveDay의 사계절 후드 집업. 폴리 혼방 소재로 가볍고 캐주얼한 루즈핏입니다.", "ink"),
        ("피케 폴로 셔츠", "상의", "폴로", 39000, "OfficeFit의 여름 폴로. 면 100% 피케 소재로 통기성이 좋은 슬림핏입니다.", "rose"),
        ("브이넥 니트 베스트", "상의", "니트베스트", 42000, "ModeLab의 가을겨울 니트 베스트. 아크릴·울 혼방으로 레이어드하기 좋은 레귤러핏입니다.", "sage"),
        ("헨리넥 롱슬리브 티", "상의", "티셔츠", 34000, "FitBasic의 봄가을 헨리넥 티셔츠. 면 95%·스판 5% 소재로 신축성 있는 슬림핏입니다.", "sand"),
        ("체크 플란넬 셔츠", "상의", "셔츠", 52000, "UrbanLine의 가을겨울 플란넬 셔츠. 면 100% 소재로 두툼하고 여유로운 릴랙스드핏입니다.", "blue"),
        ("크롭 니트", "상의", "니트", 47000, "WarmMood의 가을 크롭 니트. 아크릴 60%·울 40% 혼방으로 짧은 기장의 슬림핏입니다.", "stone"),
        ("실크 블렌드 블라우스", "상의", "블라우스", 62000, "ModeLab의 봄가을 블라우스. 폴리·레이온 혼방의 부드러운 광택이 도는 레귤러핏입니다.", "ink"),
        # 아우터 추가
        ("라이트 윈드 브레이커", "아우터", "바람막이", 55000, "ActiveDay의 봄가을 바람막이. 나일론 100% 소재로 가볍고 방풍이 되는 레귤러핏입니다.", "rose"),
        ("빈티지 데님 자켓", "아우터", "데님자켓", 79000, "DenimWorks의 사계절 데님 자켓. 면 98%·스판 2% 소재로 클래식한 스트레이트핏입니다.", "sage"),
        ("무스탕 재킷", "아우터", "무스탕", 159000, "NorthCloset의 겨울 무스탕. 폴리·울 혼방으로 보온성이 좋은 레귤러핏입니다.", "sand"),
        ("퀄팅 베스트", "아우터", "베스트", 69000, "ActiveDay의 가을겨울 퀄팅 베스트. 폴리 충전재로 가볍고 따뜻한 레귤러핏입니다.", "blue"),
        ("롱 가디건", "아우터", "가디건", 64000, "WarmMood의 가을겨울 가디건. 아크릴·울 혼방으로 여유로운 루즈핏입니다.", "stone"),
        ("클래식 트렌치 코트", "아우터", "코트", 179000, "NorthCloset의 봄가을 트렌치 코트. 폴리·레이온 혼방으로 단정한 레귤러핏입니다.", "ink"),
        ("MA-1 봄버 재킷", "아우터", "자켓", 99000, "ModeLab의 사계절 봄버 재킷. 나일론 100% 소재로 캐주얼한 오버핏입니다.", "rose"),
        ("플리스 집업 재킷", "아우터", "플리스", 58000, "ActiveDay의 가을겨울 플리스 집업. 폴리 100% 소재로 포근하고 가벼운 레귤러핏입니다.", "sage"),
        ("싱글 블레이저", "아우터", "블레이저", 129000, "ModeLab의 봄가을 블레이저. 폴리·레이온 혼방으로 단정한 슬림핏입니다.", "sand"),
        ("숏 패딩 재킷", "아우터", "패딩", 119000, "NorthCloset의 겨울 숏패딩. 폴리 충전재로 가볍고 따뜻한 레귤러핏입니다.", "blue"),
        # 하의 추가
        ("와이드 데님 팬츠", "하의", "청바지", 72000, "DenimWorks의 사계절 와이드 데님. 면 100% 소재로 넉넉한 와이드핏입니다.", "stone"),
        ("테이퍼드 슬랙스", "하의", "슬랙스", 65000, "OfficeFit의 사계절 테이퍼드 슬랙스. 폴리·레이온·스판 혼방으로 깔끔한 테이퍼드핏입니다.", "ink"),
        ("코튼 데일리 반바지", "하의", "반바지", 39000, "SummerLab의 여름 반바지. 면 100% 소재로 편안한 레귤러핏입니다.", "rose"),
        ("스탠다드 조거 팬츠", "하의", "조거팬츠", 49000, "ActiveDay의 사계절 조거 팬츠. 폴리·스판 혼방으로 활동적인 슬림핏입니다.", "sage"),
        ("유틸리티 카고 팬츠", "하의", "카고팬츠", 68000, "OfficeFit의 봄가을 카고 팬츠. 면 100% 소재로 넉넉한 릴랙스드핏입니다.", "sand"),
        ("플리츠 미니 스커트", "하의", "스커트", 45000, "UrbanLine의 봄가을 미니 스커트. 폴리 혼방으로 잔주름이 살아있는 A라인 핏입니다.", "blue"),
        ("롱 플리츠 스커트", "하의", "스커트", 54000, "UrbanLine의 가을겨울 롱 스커트. 폴리 혼방으로 우아하게 떨어지는 A라인 핏입니다.", "stone"),
        ("코듀로이 팬츠", "하의", "슬랙스", 62000, "OfficeFit의 가을겨울 코듀로이 팬츠. 면 100% 소재로 따뜻한 스트레이트핏입니다.", "ink"),
        ("하이웨이스트 데님 쇼츠", "하의", "반바지", 42000, "DenimWorks의 여름 데님 쇼츠. 면 98%·스판 2% 소재로 슬림한 핏입니다.", "rose"),
        ("부츠컷 데님 팬츠", "하의", "청바지", 74000, "DenimWorks의 사계절 부츠컷 데님. 면 100% 소재로 밑단이 살짝 퍼지는 스트레이트핏입니다.", "sage"),
    ]
    users = [
        ("김하늘", "레귤러핏", 165), ("이서준", "루즈핏", 180), ("박지우", "레귤러핏", 170),
        ("최유나", "슬림핏", 160), ("정민준", "레귤러핏", 175), ("강서연", "루즈핏", 165),
        ("조도윤", "슬림핏", 170), ("윤지호", "레귤러핏", 170), ("임채원", "슬림핏", 160),
        ("한지민", "루즈핏", 180), ("오승우", "레귤러핏", 175), ("서연우", "슬림핏", 155),
        ("신예은", "레귤러핏", 165), ("권도현", "루즈핏", 185), ("황유진", "슬림핏", 160),
        ("안준서", "레귤러핏", 175), ("송하윤", "루즈핏", 160), ("전민서", "슬림핏", 170),
        ("홍시우", "레귤러핏", 185), ("배수아", "루즈핏", 155),
    ]
    # 카테고리와 무관한 공통 리뷰 소재. 옷마다 다른 부분집합을 뽑아 내용이 겹치지 않게 합니다.
    common_fragments = [
        (5, "정사이즈이고 착용감이 좋아요. 디자인도 예뻐요."), (5, "가볍고 부드러워요. 디자인이 예뻐요."),
        (5, "마감이 좋아요. 착용감이 편안해요."), (5, "핏이 예뻐서 여러 번 재구매했어요."),
        (5, "색감이 사진이랑 똑같고 고급스러워요."), (5, "부드러운 촉감이 마음에 들어요. 디자인도 세련됐어요."),
        (5, "가벼워서 사계절 내내 잘 입어요."), (5, "마감 처리가 꼼꼼해서 오래 입을 것 같아요."),
        (4, "가벼워서 편안해요. 핏이 예뻐요."), (4, "정사이즈라 잘 맞아요. 핏이 좋아요."),
        (4, "무난하게 매일 입기 좋아요. 마감도 깔끔해요."), (4, "생각보다 만족스러워요. 재구매 의사 있어요."),
        (4, "착용감이 편안하고 디자인도 무난해요."), (4, "가격 대비 만족스러운 품질이에요."),
        (4, "핏이 슬림해서 깔끔하게 떨어져요."), (4, "부드러운 소재라 자주 손이 가요."),
        (4, "핏이 루즈해서 편하게 입기 좋아요."),
        (3, "소재가 얇아요. 디자인은 좋아요."), (3, "무난하지만 특별한 느낌은 없어요."),
        (3, "핏은 괜찮은데 세탁 후 살짝 줄었어요."), (3, "가격 대비 무난한 정도예요."),
        (3, "디자인은 예쁜데 소재가 조금 아쉬워요."), (3, "평범하지만 데일리로 입기엔 괜찮아요."),
        (2, "소재가 생각보다 얇아서 비쳐요."), (2, "생각보다 얇아서 계절감이 안 맞아요."),
        (1, "디자인이 예쁘지 않아요. 재질도 별로예요."), (1, "하나도 안 편안해요. 실망했어요."),
        (1, "마감이 엉성해서 실밥이 보여요."), (1, "생각했던 색상과 많이 달라요."),
    ]
    top_fragments = [
        (2, "사이즈가 커요. 소매가 길어요."), (2, "사이즈가 작아요. 조금 타이트해요."),
        (2, "소매가 짧아서 손목이 드러나요."),
        (1, "소매가 너무 길어서 불편해요."), (1, "생각보다 타이트해서 답답해요."),
    ]
    bottom_fragments = [
        (2, "사이즈가 커요. 기장이 길어요."), (2, "사이즈가 작아요. 조금 타이트해요."),
        (2, "허리가 커서 벨트가 필요해요."), (2, "허리가 작아서 불편해요."), (2, "기장이 짧아서 아쉬워요."),
        (1, "사이즈가 안 맞아서 반품했어요. 허리가 너무 작아요."), (1, "기장이 너무 길어서 줄였어요."),
        (1, "허리가 너무 커서 흘러내려요."),
    ]
    with connection:
        connection.executemany("INSERT INTO users VALUES (?,?,?,?)", [
            (uid, name, fit, height) for uid, (name, fit, height) in enumerate(users, 1)])
        user_ids = list(range(1, len(users) + 1))
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
                uid = user_ids[j % len(user_ids)]
                size = ("S", "M", "L")[(j // 3 + pid) % 3]
                cursor = connection.execute(
                    "INSERT INTO orders(user_id,product_id,size,ordered_at) VALUES (?,?,?,?)",
                    (uid, pid, size, f"2026-08-{j + 1:02d}"))
                if (j + pid) % 5 == 0 or (uid == 1 and size == "L" and j % 2 == 0):
                    connection.execute("INSERT INTO returns(order_id,reason,returned_at) VALUES (?,?,?)",
                                       (cursor.lastrowid, "사이즈 큼" if size == "L" else "핏 불일치", "2026-08-28"))
            # 상품마다 다른 무작위 부분집합을 뽑아 리뷰 구성이 겹치지 않게 하되, 같은 시드로
            # 재실행해도 항상 같은 결과가 나오도록 상품 id를 시드로 고정합니다.
            rng = random.Random(pid)
            pool = common_fragments + (bottom_fragments if item[1] == "하의" else top_fragments)
            picks = rng.sample(pool, rng.randint(10, 30))
            for j, (rating, content) in enumerate(picks):
                uid = rng.choice(user_ids)
                size = rng.choice(("S", "M", "L"))
                month, day = rng.choice((6, 7, 8)), rng.randint(1, 28)
                connection.execute(
                    "INSERT INTO reviews(user_id,product_id,size,rating,content,created_at) VALUES (?,?,?,?,?,?)",
                    (uid, pid, size, rating, content, f"2026-{month:02d}-{day:02d}"))


if __name__ == "__main__":
    initialize()
    print("DB 준비 완료. 기존 데이터는 유지했습니다.")
