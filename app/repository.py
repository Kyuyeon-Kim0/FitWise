"""SQL 접근 담당. UI와 분석 모듈의 공통 데이터 접근 계층."""
import json


def list_products(connection, category="전체"):
    if category not in ("전체", "상의", "아우터", "하의"):
        raise ValueError("유효하지 않은 카테고리입니다.")
    return [dict(row) for row in connection.execute(
        """SELECT p.*,AVG(r.rating) AS rating,COUNT(r.id) AS review_count FROM products p
           LEFT JOIN reviews r ON r.product_id=p.id WHERE (?='전체' OR p.category=?)
           GROUP BY p.id ORDER BY p.id""", (category, category))]


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


def list_users(connection):
    return [dict(row) for row in connection.execute("SELECT * FROM users ORDER BY id")]
