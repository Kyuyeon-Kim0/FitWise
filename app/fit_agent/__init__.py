"""투명한 가중합 지표. 반품 확률이나 학습된 AI 모델의 예측이 아닙니다."""
import pandas as pd

WEIGHTS = {"personal_size": 0.25, "product": 0.20, "product_size": 0.30, "review": 0.25}


def analyze(connection, user_id, product, size, review_result, height, weight):
    frame = pd.read_sql_query(
        """SELECT o.user_id,o.product_id,o.size,p.category,u.height,u.weight,
                  CASE WHEN r.id IS NULL THEN 0 ELSE 1 END AS returned
           FROM orders o JOIN products p ON p.id=o.product_id JOIN users u ON u.id=o.user_id
           LEFT JOIN returns r ON r.order_id=o.id
           WHERE o.user_id=? OR o.product_id=?""", connection, params=(user_id, product["id"]))
    personal = frame[(frame.user_id == user_id) & (frame.category == product["category"])]
    product_orders = frame[frame.product_id == product["id"]]
    review_bodies = pd.read_sql_query(
        """SELECT r.rating,u.height,u.weight FROM reviews r JOIN users u ON u.id=r.user_id
           WHERE r.product_id=?""", connection, params=(product["id"],))

    def metric(label, subset, weight):
        n = len(subset)
        returned = int(subset.returned.sum())
        success = round((n - returned) / n * 100, 1) if n else None
        return {"label": label, "count": n, "returned": returned, "success_pct": success,
                "value": success, "weight": weight, "is_return_rate": False}

    def body_weighted_metric(label, subset, metric_weight):
        if subset.empty:
            return {"label": label, "count": 0, "returned": 0, "success_pct": None,
                    "value": None, "weight": metric_weight, "is_return_rate": False,
                    "similar_count": 0}
        height_gap = (subset.height - height).abs()
        weight_gap = (subset.weight - weight).abs()
        similarity = (1 - (height_gap.clip(upper=20) / 20) * 0.5
                      - (weight_gap.clip(upper=20) / 20) * 0.5).clip(lower=0.1)
        success = round((similarity * (1 - subset.returned)).sum() / similarity.sum() * 100, 1)
        return {"label": label, "count": len(subset), "returned": int(subset.returned.sum()),
                "success_pct": success, "value": success, "weight": metric_weight,
                "is_return_rate": False,
                "similar_count": int(((height_gap <= 10) & (weight_gap <= 10)).sum())}

    def review_metric():
        if review_bodies.empty:
            return {"label": "리뷰 적합도 · 체형 유사 가중 긍정 비율", "count": 0,
                    "success_pct": None, "value": None, "weight": WEIGHTS["review"],
                    "is_return_rate": False, "similar_count": 0}
        height_gap = (review_bodies.height - height).abs()
        weight_gap = (review_bodies.weight - weight).abs()
        # 키 20cm, 몸무게 20kg 차이부터는 최소 가중치(0.1)를 적용합니다.
        similarity = (1 - (height_gap.clip(upper=20) / 20) * 0.5
                      - (weight_gap.clip(upper=20) / 20) * 0.5).clip(lower=0.1)
        score = round((similarity * (review_bodies.rating >= 4)).sum() / similarity.sum() * 100, 1)
        similar_count = int(((height_gap <= 10) & (weight_gap <= 10)).sum())
        return {"label": "리뷰 적합도 · 체형 유사 가중 긍정 비율", "count": len(review_bodies),
                "success_pct": score, "value": score, "weight": WEIGHTS["review"],
                "is_return_rate": False, "similar_count": similar_count}

    metrics = [
        metric("개인 선택 사이즈 성공률 · 동일 카테고리", personal[personal['size'] == size], WEIGHTS["personal_size"]),
        metric("상품 반품 안정성", product_orders, WEIGHTS["product"]),
        body_weighted_metric("체형 유사 선택 사이즈 성공률",
                             product_orders[product_orders['size'] == size], WEIGHTS["product_size"]),
        review_metric(),
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
    reasons.append(f"선택 사이즈의 상품 구매 표본은 {metrics[2]['count']}건이며, 체형 유사 구매자는 {metrics[2]['similar_count']}건입니다.")
    reasons.append(f"리뷰 표본은 {review_result['count']}건입니다.")
    reasons.append(f"입력한 체형(키 {height}cm · 몸무게 {weight}kg)과 키 ±10cm·몸무게 ±10kg 이내인 리뷰는 {metrics[3]['similar_count']}건입니다.")
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
