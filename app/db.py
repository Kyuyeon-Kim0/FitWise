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
        # 키 컬럼 도입 전 DB의 기존 사용자 데이터는 기본값으로 보존합니다.
        user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
        if user_columns and "height" not in user_columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN height INTEGER NOT NULL DEFAULT 165 "
                "CHECK(height BETWEEN 140 AND 200)"
            )
            connection.commit()
        user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
        if user_columns and "weight" not in user_columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN weight INTEGER NOT NULL DEFAULT 60 "
                "CHECK(weight BETWEEN 35 AND 180)"
            )
            connection.commit()

        # 이전 DB의 리뷰 캐시는 상품당 하나였으므로 baseline 결과로 보존해 이전합니다.
        review_columns = {row["name"] for row in connection.execute("PRAGMA table_info(review_analysis)")}
        if review_columns and "mode" not in review_columns:
            connection.execute("DROP INDEX IF EXISTS idx_review_analysis_product")
            connection.execute("ALTER TABLE review_analysis RENAME TO review_analysis_legacy")
            connection.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
            connection.execute("""INSERT INTO review_analysis(id,product_id,mode,result_json,created_at)
                                  SELECT id,product_id,'baseline',result_json,created_at
                                  FROM review_analysis_legacy""")
            connection.execute("DROP TABLE review_analysis_legacy")
            connection.commit()

        # 버튼 클릭(requested)과 작업 완료(completed)를 모두 기록하도록 기존 로그를 확장합니다.
        agent_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='agent_logs'"
        ).fetchone()
        if agent_row and "'started'" not in agent_row["sql"]:
            connection.execute("DROP INDEX IF EXISTS idx_agents_request")
            connection.execute("ALTER TABLE agent_logs RENAME TO agent_logs_legacy")
            connection.execute("""CREATE TABLE agent_logs (
                id INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
                agent_type TEXT NOT NULL CHECK(agent_type IN ('review','fit')),
                product_id INTEGER REFERENCES products(id), user_id INTEGER REFERENCES users(id), size TEXT,
                status TEXT NOT NULL CHECK(status IN ('started','success','error')),
                processing_ms REAL NOT NULL, result_json TEXT, error_type TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )""")
            connection.execute("""INSERT INTO agent_logs
                (id,request_id,agent_type,product_id,user_id,size,status,processing_ms,result_json,error_type,created_at)
                SELECT id,request_id,agent_type,product_id,user_id,size,status,processing_ms,result_json,error_type,created_at
                FROM agent_logs_legacy""")
            connection.execute("DROP TABLE agent_logs_legacy")
            connection.execute("CREATE INDEX idx_agents_request ON agent_logs(request_id)")
            connection.commit()

        resource_columns = {row["name"] for row in connection.execute("PRAGMA table_info(resource_logs)")}
        if resource_columns and "phase" not in resource_columns:
            connection.execute("DROP INDEX IF EXISTS idx_resources_operation")
            connection.execute("ALTER TABLE resource_logs RENAME TO resource_logs_legacy")
            connection.execute("""CREATE TABLE resource_logs (
                id INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
                operation TEXT NOT NULL CHECK(operation IN ('browse','review','fit')),
                phase TEXT NOT NULL CHECK(phase IN ('requested','completed')),
                cpu_percent REAL NOT NULL, cpu_ms REAL NOT NULL,
                memory_before_mb REAL NOT NULL, memory_after_mb REAL NOT NULL,
                memory_delta_mb REAL NOT NULL, processing_ms REAL NOT NULL, response_ms REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('started','success','error')),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )""")
            connection.execute("""INSERT INTO resource_logs
                (id,request_id,operation,phase,cpu_percent,cpu_ms,memory_before_mb,memory_after_mb,
                 memory_delta_mb,processing_ms,response_ms,status,created_at)
                SELECT id,request_id,operation,'completed',cpu_percent,cpu_ms,memory_before_mb,memory_after_mb,
                 memory_delta_mb,processing_ms,response_ms,status,created_at FROM resource_logs_legacy""")
            connection.execute("DROP TABLE resource_logs_legacy")
            connection.execute("CREATE INDEX idx_resources_operation ON resource_logs(operation)")
            connection.execute("CREATE INDEX idx_resources_request ON resource_logs(request_id)")
            connection.commit()

        # 다른 개발 작업의 기존 DB를 자동 변경하지 않습니다.
        expected = {
            "users": {"id", "name", "preferred_fit", "height", "weight"},
            "products": {"id", "subcategory", "sizes", "measurements"},
            "orders": {"id", "user_id", "product_id", "size", "ordered_at"},
            "returns": {"id", "order_id", "reason", "returned_at"},
            "reviews": {"id", "user_id", "product_id", "size", "rating", "content", "created_at"},
            "review_analysis": {"id", "product_id", "mode", "result_json", "created_at"},
            "agent_logs": {"id", "request_id", "agent_type", "processing_ms", "result_json", "status"},
            "resource_logs": {"id", "request_id", "operation", "phase", "memory_after_mb", "response_ms", "status"},
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
    # 실제 온라인 쇼핑몰 리뷰의 어투·소재를 참고해 새로 작성한 문장들입니다(특정 리뷰 원문 인용 아님).
    common_fragments = [
        (5, "착용감이 좋아서 이 브랜드 제품만 벌써 세 번째 구매하고 있어요. 이번에도 기대를 저버리지 않네요."),
        (5, "디자인이 예뻐서 옷장에 걸어만 놔도 기분이 좋아지는 아이템이에요. 데일리로 자주 손이 갈 것 같습니다."),
        (5, "가벼워서 계절 상관없이 자주 꺼내 입게 돼요. 활동성도 좋고 구김도 잘 안 생겨서 만족도가 높습니다."),
        (5, "마감이 좋아서 실밥 하나 삐져나온 곳 없이 깔끔해요. 박음질도 꼼꼼해서 오래 입을 수 있을 것 같습니다."),
        (5, "촉감이 부드러워서 맨살에 바로 입어도 까슬거림이 전혀 없어요. 예민한 편인데도 편안하게 입었습니다."),
        (5, "사진과 색감 차이가 거의 없어서 만족스럽고, 생각보다 고급스러운 소재감에 놀랐어요."),
        (5, "정사이즈로 주문했는데 예상한 대로 딱 떨어져서 실측표를 믿고 사도 되겠다 싶었습니다."),
        (5, "세탁 후에도 목둘레가 늘어나지 않고 형태가 그대로 유지돼서 관리하기 편한 아이템이에요."),
        (5, "포장부터 꼼꼼해서 받는 순간부터 기분이 좋았고, 상품 상태도 흠 잡을 데 없이 깨끗했습니다."),
        (5, "핏이 예뻐서 어떤 하의와 매치해도 잘 어울려요. 이미 다른 컬러로 추가 구매를 고민 중입니다."),
        (5, "가격 대비 품질이 훌륭해서 같은 가격대 다른 브랜드보다 훨씬 만족스러운 선택이었어요."),
        (5, "기본템으로 사기 좋고, 무난하면서도 핏이 살아 있어서 자주 손이 가는 옷이 됐습니다."),
        (4, "전체적으로 만족스럽고 핏도 무난해서 데일리로 편하게 입기 좋아요. 재구매 의사 있습니다."),
        (4, "가벼워서 편안하게 입기 좋고, 디자인도 심플해서 여러 스타일에 두루 활용하기 좋습니다."),
        (4, "생각했던 것보다 만족스럽고 착용감도 편안한 편이라 자주 입게 될 것 같아요."),
        (4, "핏이 슬림해서 깔끔한 인상을 주는 아이템이에요. 다만 다음엔 한 치수 위로 도전해볼까 합니다."),
        (4, "부드러운 소재라 자주 손이 가고, 무난한 컬러라 어디에나 잘 어울려서 데일리로 좋습니다."),
        (4, "마감도 깔끔하고 색상도 화면과 비슷하게 나와서 무난하게 만족스러운 구매였어요."),
        (4, "정사이즈로 잘 맞았고 활동성도 나쁘지 않아서 편하게 입고 있습니다."),
        (4, "재질이 튼튼한 편이라 오래 입을 수 있을 것 같고, 세탁 후에도 큰 변형은 없었어요."),
        (4, "핏이 루즈해서 편하게 걸치기 좋고, 레이어드하기에도 부담 없는 두께감입니다."),
        (4, "가격 대비 만족스러운 품질이라 부담 없이 하나 더 구매할 의향이 있어요."),
        (3, "소재가 얇아요. 그래도 디자인은 예뻐서 얇은 아우터 안에 레이어드용으로 입으려고 합니다."),
        (3, "무난하지만 특별한 느낌은 없어서 그냥 기본템 하나 채웠다는 느낌이에요."),
        (3, "핏은 나쁘지 않은데 세탁 한 번 했더니 살짝 줄어든 느낌이라 다음엔 한 치수 크게 사려고요."),
        (3, "가격 대비 무난한 정도이지, 기대했던 것만큼 특별한 감동은 없었습니다."),
        (3, "디자인은 예쁜데 소재가 생각보다 아쉬워서 별 다섯 개까지는 못 주겠어요."),
        (3, "평범하지만 데일리로 입기엔 크게 불편함 없이 무난한 편입니다."),
        (3, "색상이 화면이랑 미묘하게 달라서 처음엔 당황했는데, 입어보니 나쁘지 않았어요."),
        (3, "핏이 애매하게 크지도 작지도 않아서 정사이즈인지 판단하기가 살짝 어려웠습니다."),
        (3, "재질은 평범한 편이고 딱히 특별한 장점도 단점도 없는 무난한 아이템이었어요."),
        (3, "실측표랑 실제 착용감이 살짝 다르게 느껴져서 다음엔 사이즈를 더 신중히 골라야 할 것 같습니다."),
        (2, "소재가 생각보다 얇아서 비쳐요. 안에 이너를 꼭 받쳐 입어야 할 것 같습니다."),
        (2, "생각보다 얇아서 계절감이 안 맞는 느낌이라 활용도가 좀 아쉬웠어요."),
        (2, "세탁 후에 살짝 줄어든 느낌이 들어서 다음엔 손세탁을 고려해야 할 것 같아요."),
        (2, "받았을 때 먼지가 좀 묻어 있어서 새 상품인지 의아했지만, 세탁하고 입으니 괜찮았습니다."),
        (2, "생각했던 색감과 미묘하게 달라서 반품을 고민했지만 그냥 입기로 했어요."),
        (2, "목 부분이 세탁 몇 번에 살짝 늘어나는 느낌이라 관리에 신경 써야 할 것 같습니다."),
        (2, "봉제선이 한쪽이 살짝 삐뚤어진 느낌이 있어서 아쉬웠어요."),
        (1, "디자인이 예쁘지 않아요. 사진과 실물 차이가 커서 실망스러웠습니다."),
        (1, "하나도 안 편안해요. 재질도 뻣뻣하고 기대했던 것과 많이 달라서 실망했습니다."),
        (1, "마감이 엉성해서 실밥이 여기저기 보이고 박음질도 고르지 않았어요."),
        (1, "생각했던 색상과 많이 달라서 반품 절차를 알아보고 있습니다."),
        (1, "배송은 빨랐지만 상품 상태가 기대 이하라 교환을 고민하고 있어요."),
        (1, "가격 대비 퀄리티가 아쉬워서 재구매 의사는 없을 것 같습니다."),
    ]
    top_fragments = [
        (5, "어깨선이 자연스럽게 떨어지고 소매 길이도 딱 알맞아서 실측표 그대로 믿고 사도 되겠습니다."),
        (5, "목 시보리가 짱짱해서 늘어남 걱정 없이 오래 입을 수 있을 것 같아요."),
        (5, "정핏에서 세미 오버핏 사이의 실루엣이라 다양한 체형에 무난하게 잘 어울릴 것 같습니다."),
        (4, "핏이 슬림해서 깔끔하게 떨어지고, 어깨선도 딱 맞아서 만족스러웠습니다."),
        (4, "핏이 루즈해서 편하게 걸치기 좋고, 오버핏 느낌을 원했다면 만족할 거예요."),
        (3, "소매 길이가 살짝 애매해서 걷어 입을지 말지 고민되는 길이였어요."),
        (2, "사이즈가 커요. 소매가 길어서 걷어 입어야 했습니다."),
        (2, "사이즈가 작아요. 조금 타이트해서 다음엔 한 치수 크게 주문할 것 같습니다."),
        (2, "소매가 짧아서 손목이 훤히 드러나는 느낌이라 아쉬웠어요."),
        (2, "어깨선이 살짝 좁게 떨어져서 활동할 때 약간 불편함이 있었습니다."),
        (2, "목둘레가 생각보다 타이트해서 답답한 느낌이 있었어요."),
        (1, "소매가 너무 길어서 불편해요. 결국 수선을 맡겨야 할 것 같습니다."),
        (1, "생각보다 타이트해서 답답해요. 사이즈를 잘못 고른 것 같습니다."),
        (1, "어깨가 좁아서 움직일 때마다 당기는 느낌이 있어 오래 입기 힘들었어요."),
    ]
    bottom_fragments = [
        (5, "허리 사이즈가 실측표 그대로 딱 맞아서 벨트 없이도 편하게 입었습니다."),
        (5, "기장이 발목에서 살짝 떨어지는 길이라 신발과의 밸런스가 예뻤어요."),
        (5, "허벅지부터 밑단까지 떨어지는 라인이 예뻐서 태가 잘 살았습니다."),
        (5, "허리 단면이 넉넉한 편이라 체형 상관없이 편하게 입기 좋을 것 같아요."),
        (4, "허리 밴딩이 적당히 여유 있어서 오래 앉아 있어도 편했습니다."),
        (4, "기장이 딱 적당해서 별도 수선 없이 바로 입을 수 있었어요."),
        (3, "허벅지 부분이 살짝 여유 있는 편이라 활동하기엔 편했지만 핏은 다소 루즈했습니다."),
        (2, "사이즈가 커요. 기장이 길어서 밑단을 접어 입어야 했습니다."),
        (2, "사이즈가 작아요. 조금 타이트해서 활동하기 살짝 불편했어요."),
        (2, "허리가 커서 벨트 없이는 흘러내리는 느낌이 있었습니다."),
        (2, "허리가 작아서 오래 앉아 있으면 조이는 느낌이 있었어요."),
        (2, "기장이 짧아서 발목이 훤히 드러나는 게 아쉬웠습니다."),
        (2, "허벅지 부분이 타이트해서 움직일 때 조금 불편했어요."),
        (1, "사이즈가 안 맞아서 결국 반품했어요. 허리가 너무 작게 나온 것 같습니다."),
        (1, "기장이 너무 길어서 수선 맡기지 않으면 입기 힘든 길이였습니다."),
        (1, "허리가 너무 커서 몇 번을 흘러내려서 결국 반품했어요."),
    ]
    with connection:
        connection.executemany("INSERT INTO users VALUES (?,?,?,?,?)", [
            (uid, name, fit, height, round((height - 100) * 0.9 + ((uid % 5) - 2) * 2))
            for uid, (name, fit, height) in enumerate(users, 1)])
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
