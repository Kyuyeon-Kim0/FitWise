"""투명한 가중합 지표. 반품 확률이나 학습된 AI 모델의 예측이 아닙니다."""
import pandas as pd

WEIGHTS = {"personal_size": 0.30, "product": 0.20, "product_size": 0.25, "review": 0.25}


def analyze(connection, user_id, product, size, review_result):
    frame = pd.read_sql_query(
        """SELECT o.user_id,o.product_id,o.size,p.category,
                  CASE WHEN r.id IS NULL THEN 0 ELSE 1 END AS returned
           FROM orders o JOIN products p ON p.id=o.product_id
           LEFT JOIN returns r ON r.order_id=o.id
           WHERE o.user_id=? OR o.product_id=?""", connection, params=(user_id, product["id"]))
    personal = frame[(frame.user_id == user_id) & (frame.category == product["category"])]
    product_orders = frame[frame.product_id == product["id"]]

    def metric(label, subset, weight):
        n = len(subset)
        returned = int(subset.returned.sum())
        success = round((n - returned) / n * 100, 1) if n else None
        return {"label": label, "count": n, "returned": returned, "success_pct": success,
                "value": success, "weight": weight, "is_return_rate": False}

    metrics = [
        metric("개인 선택 사이즈 성공률 · 동일 카테고리", personal[personal['size'] == size], WEIGHTS["personal_size"]),
        metric("상품 반품 안정성", product_orders, WEIGHTS["product"]),
        metric("선택 사이즈 반품 안정성", product_orders[product_orders['size'] == size], WEIGHTS["product_size"]),
        {"label": "리뷰 적합도 · 긍정 평점 비율", "count": review_result["count"],
         "success_pct": review_result["positive_pct"], "value": review_result["positive_pct"],
         "weight": WEIGHTS["review"], "is_return_rate": False},
    ]
    available = [m for m in metrics if m["success_pct"] is not None]
    total_weight = sum(m["weight"] for m in available)
    score = round(sum(m["success_pct"] * m["weight"] for m in available) / total_weight) if available else None
    for m in metrics:
        m["effective_weight_pct"] = round(m["weight"] / total_weight * 100, 1) if m in available else 0
    reasons = []
    selected = metrics[1]
    if selected["count"]:
        reasons.append(f"동일 카테고리의 {size} 사이즈 구매 {selected['count']}건 중 {selected['returned']}건을 반품했습니다.")
    else:
        reasons.append(f"동일 카테고리의 {size} 사이즈 구매 이력이 없어 해당 항목은 계산에서 제외했습니다.")
    reasons.append(f"선택 사이즈의 상품 구매 표본은 {metrics[2]['count']}건, 리뷰 표본은 {review_result['count']}건입니다.")
    keywords = [x["keyword"] for x in review_result["negative_keywords"][:3]]
    if keywords:
        reasons.append(f"리뷰에서 {', '.join(keywords)} 의견이 발견되어 실측표 확인을 권장합니다.")
    sparse = any(m["count"] < 5 for m in metrics)
    if sparse:
        reasons.append("일부 항목의 표본이 5건 미만입니다. 점수를 참고용으로만 활용해 주세요.")
    return {"mode": "weighted-baseline-v1", "score": score, "size": size, "metrics": metrics,
            "reasons": reasons, "limited_data": sparse,
            "label": "데이터 부족" if score is None else "잘 맞을 가능성을 살펴보세요" if score >= 80 else "실측 확인을 권장해요" if score >= 60 else "사이즈를 신중히 비교해 보세요",
            "disclaimer": "내부 구매적합도 지표이며 실제 반품 확률이나 구매 성공 확률이 아닙니다."}
