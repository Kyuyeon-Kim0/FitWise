"""공통 실행 경로. UI는 분석 버튼을 눌렀을 때만 이 모듈을 호출합니다."""
from app.config import get_settings
from app.db import connect
from app.fit_agent import analyze as analyze_fit
from app.monitoring import measure
from app.repository import get_product, list_products, list_reviews
from app.review_agent import analyze as analyze_reviews
from app.review_agent import analyze_api as analyze_reviews_api


def ensure_baseline():
    if get_settings().analysis_mode != "baseline":
        raise ValueError("현재는 baseline 모드만 지원합니다. 실제 API 연결은 후속 개발 항목입니다.")


def browse_products(category="전체", database=None):
    with connect(database) as connection:
        with measure(connection, "browse"):
            return list_products(connection, category)


def browse_detail(product_id, database=None):
    with connect(database) as connection:
        with measure(connection, "browse"):
            return get_product(connection, product_id), list_reviews(connection, product_id)


def run_review(product_id, database=None, *, mode=None):
    settings = get_settings()
    mode = mode or settings.analysis_mode
    if mode not in ("baseline", "api"):
        raise ValueError("지원하지 않는 분석 모드입니다.")
    if mode == "api" and not settings.api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다. baseline 모드를 사용하세요.")
    with connect(database) as connection:
        get_product(connection, product_id)
        with measure(connection, "review") as task:
            reviews = list_reviews(connection, product_id)
            if mode == "api":
                result = task.run_agent("review", lambda: analyze_reviews_api(reviews, settings.api_key, settings.model), product_id)
            else:
                result = task.run_agent("review", lambda: analyze_reviews(reviews), product_id)
        return {"result": result, "request_id": task.request_id}


def run_fit(product_id, user_id, size, database=None):
    ensure_baseline()
    with connect(database) as connection:
        product = get_product(connection, product_id)
        if type(user_id) is not int or not isinstance(size, str) or size not in product["sizes"]:
            raise ValueError("사용자와 상품 사이즈를 확인해 주세요.")
        if connection.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone() is None:
            raise ValueError("사용자를 찾을 수 없습니다.")

        with measure(connection, "fit") as task:
            def pipeline():
                review = task.run_agent("review", lambda: analyze_reviews(list_reviews(connection, product_id)),
                                        product_id, user_id, size, top_level=False)
                return analyze_fit(connection, user_id, product, size, review)
            result = task.run_agent("fit", pipeline, product_id, user_id, size)
        return {"result": result, "request_id": task.request_id,
                "product_id": product_id, "user_id": user_id, "size": size}
