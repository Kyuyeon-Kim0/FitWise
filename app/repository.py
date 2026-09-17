"""SQL 접근 담당. UI와 분석 모듈의 공통 데이터 접근 계층."""
import json


SORT_OPTIONS = {
    "추천순": "p.id",
    "신상품순": "p.id DESC",
    "가격 낮은순": "p.price ASC",
    "가격 높은순": "p.price DESC",
    "리뷰 많은순": "review_count DESC",
    "평점 높은순": "rating DESC",
}


def list_products(connection, category="전체", search="", sort="추천순", limit=None, offset=0):
    """상품 목록 조회. limit/offset은 SQL 레벨 페이지네이션으로 처리해 상품 수가 늘어도 매번 전체를 불러오지 않습니다."""
    if category not in ("전체", "상의", "아우터", "하의"):
        raise ValueError("유효하지 않은 카테고리입니다.")
    if sort not in SORT_OPTIONS:
        raise ValueError("유효하지 않은 정렬 기준입니다.")
    query = f"""SELECT p.*,AVG(r.rating) AS rating,COUNT(r.id) AS review_count FROM products p
           LEFT JOIN reviews r ON r.product_id=p.id
           WHERE (?='전체' OR p.category=?) AND (?='' OR p.name LIKE ? OR p.subcategory LIKE ?)
           GROUP BY p.id ORDER BY {SORT_OPTIONS[sort]}"""
    params = [category, category, search, f"%{search}%", f"%{search}%"]
    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params += [limit, offset]
    return [dict(row) for row in connection.execute(query, params)]


def get_product(connection, product_id):
    row = connection.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if row is None:
        raise ValueError("상품을 찾을 수 없습니다.")
    product = dict(row)
    product["sizes"] = json.loads(product["sizes"])
    product["measurements"] = json.loads(product["measurements"])
    return product


def list_reviews(connection, product_id):
    return [dict(row) for row in connection.execute(
        """SELECT r.*,u.name AS user_name FROM reviews r JOIN users u ON u.id=r.user_id
           WHERE product_id=? ORDER BY r.created_at DESC,r.id DESC""", (product_id,))]


def get_review_analysis(connection, product_id, mode):
    """상품·분석 모드(baseline/api)별로 저장된 Review Agent 결과를 반환합니다."""
    row = connection.execute(
        "SELECT result_json, created_at FROM review_analysis WHERE product_id=? AND mode=?", (product_id, mode)
    ).fetchone()
    if row is None:
        return None
    result = json.loads(row["result_json"])
    result["created_at"] = row["created_at"]
    return result


def save_review_analysis(connection, product_id, mode, result):
    """동일 상품·모드 조합의 분석 결과는 하나만 보관하고 최신 결과로 교체합니다."""
    payload = json.dumps(result, ensure_ascii=False)
    connection.execute(
        """INSERT INTO review_analysis(product_id, mode, result_json) VALUES (?, ?, ?)
           ON CONFLICT(product_id, mode) DO UPDATE SET result_json=excluded.result_json,
               created_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')""",
        (product_id, mode, payload),
    )
    connection.commit()


def list_users(connection):
    return [dict(row) for row in connection.execute("SELECT * FROM users ORDER BY id")]
