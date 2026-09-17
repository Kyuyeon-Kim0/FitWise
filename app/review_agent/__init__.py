"""평점/키워드 기반 baseline. LLM 도입 시 analyze의 반환 규격을 유지하세요."""
from collections import Counter

POSITIVE = {"착용감": ("착용감이 좋아", "편안"), "디자인": ("디자인도 예", "디자인이 예", "디자인은 좋아"),
            "가벼움": ("가벼", "가볍"), "마감": ("마감이 좋아",), "부드러움": ("부드러",)}
NEGATIVE = {"사이즈 큼": ("사이즈가 커", "사이즈 큼"), "사이즈 작음": ("사이즈가 작", "사이즈 작음"),
            "소매 길음": ("소매가 길",), "기장 길음": ("기장이 길",),
            "소재 얇음": ("소재가 얇",), "타이트함": ("타이트",)}


def analyze(reviews):
    rows = [dict(row) for row in reviews]
    count = len(rows)
    positive, negative = Counter(), Counter()
    size_comments, fit_comments = [], []
    complaints = 0
    for row in rows:
        text = row["content"]
        for label, words in POSITIVE.items():
            if any(word in text for word in words):
                positive[label] += 1
        for label, words in NEGATIVE.items():
            if any(word in text for word in words):
                negative[label] += 1
        if any(word in text for word in ("사이즈", "소매", "기장", "허리")):
            size_comments.append(text)
        if any(word in text for word in ("핏", "타이트", "루즈", "품")):
            fit_comments.append(text)
        if any(any(word in text for word in words) for key, words in NEGATIVE.items() if key != "소재 얇음"):
            complaints += 1
    rate = lambda n: round(n / count * 100, 1) if count else None
    pos = rate(sum(row["rating"] >= 4 for row in rows))
    neg = rate(sum(row["rating"] <= 2 for row in rows))
    neutral = rate(sum(row["rating"] == 3 for row in rows))
    summary = (f"리뷰 {count}건 중 긍정 평점(4~5점)은 {pos}%입니다. "
               f"주요 주의 키워드는 {', '.join(key for key, _ in negative.most_common(3)) or '없음'}입니다."
               if count else "리뷰가 없어 분석할 수 없습니다. 실측 정보를 확인해 주세요.")
    return {"mode": "rule-based-v1", "count": count, "positive_pct": pos, "negative_pct": neg,
            "neutral_pct": neutral, "size_complaint_pct": rate(complaints),
            "positive_keywords": [{"keyword": k, "count": v} for k, v in positive.most_common(5)],
            "negative_keywords": [{"keyword": k, "count": v} for k, v in negative.most_common(5)],
            "size_comments": size_comments[:4], "fit_comments": fit_comments[:4], "summary": summary}
