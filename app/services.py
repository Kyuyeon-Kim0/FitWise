"""공통 실행 경로. UI는 분석 버튼을 눌렀을 때만 이 모듈을 호출합니다."""
from app.config import get_settings
from app.db import connect
from app.fit_agent import analyze as analyze_fit
from app.monitoring import measure
from app.repository import (get_product, get_review_analysis, list_products, list_reviews,
                            save_review_analysis)
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


def get_or_run_review_analysis(connection, product_id, mode, task=None, user_id=None, size=None,
                               top_level=False):
    """모드(baseline/api)별로 저장된 결과를 우선 사용하고, 없을 때에만 Review Agent를 실행합니다."""
    cached = get_review_analysis(connection, product_id, mode)
    if cached is not None:
        cached.pop("created_at", None)
        return cached, "cached"

    reviews = list_reviews(connection, product_id)
    if mode == "api":
        settings = get_settings()
        callback = lambda: analyze_reviews_api(reviews, settings.api_key, settings.model)
    else:
        callback = lambda: analyze_reviews(reviews)
    result = (task.run_agent("review", callback, product_id, user_id, size, top_level=top_level)
              if task is not None else callback())
    save_review_analysis(connection, product_id, mode, result)
    return result, "generated"


def run_review(product_id, database=None, *, mode=None):
    settings = get_settings()
    mode = mode or settings.analysis_mode
    if mode not in ("baseline", "api"):
        raise ValueError("지원하지 않는 분석 모드입니다.")
    if mode == "api" and not settings.api_key:
        raise ValueError("OpenAI API 키가 설정되지 않았습니다. baseline 모드를 사용하세요.")
    with connect(database) as connection:
        get_product(connection, product_id)
        cached = get_review_analysis(connection, product_id, mode)
        if cached is not None:
            cached.pop("created_at", None)
            return {"result": cached, "request_id": None, "review_source": "cached"}
        with measure(connection, "review") as task:
            result, source = get_or_run_review_analysis(connection, product_id, mode, task, top_level=True)
        return {"result": result, "request_id": task.request_id, "review_source": source}


def run_fit(product_id, user_id, size, database=None):
    ensure_baseline()
    with connect(database) as connection:
        product = get_product(connection, product_id)
        if type(user_id) is not int or not isinstance(size, str) or size not in product["sizes"]:
            raise ValueError("사용자와 상품 사이즈를 확인해 주세요.")
        if connection.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone() is None:
            raise ValueError("사용자를 찾을 수 없습니다.")

        with measure(connection, "fit") as task:
            review_context = {}

            def pipeline():
                review, review_source = get_or_run_review_analysis(connection, product_id, "baseline", task, user_id, size)
                review_context["source"] = review_source
                return analyze_fit(connection, user_id, product, size, review)
            result = task.run_agent("fit", pipeline, product_id, user_id, size)
        return {"result": result, "request_id": task.request_id,
                "product_id": product_id, "user_id": user_id, "size": size,
                "review_source": review_context["source"]}
