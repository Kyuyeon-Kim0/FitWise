"""평점/키워드 기반 baseline 리뷰 분석. 정해진 규칙으로 빠르고 저렴하게 통계를 냅니다.
자유 질문에 답하는 AI 에이전트는 app/review_agent/qa_agent.py를 참고하세요."""
from collections import Counter

POSITIVE = {"착용감": ("착용감이 좋아", "편안"), "디자인": ("디자인도 예", "디자인이 예", "디자인은 좋아"),
            "가벼움": ("가벼", "가볍"), "마감": ("마감이 좋아",), "부드러움": ("부드러",)}
NEGATIVE = {"사이즈 큼": ("사이즈가 커", "사이즈 큼"), "사이즈 작음": ("사이즈가 작", "사이즈 작음"),
            "소매 길음": ("소매가 길",), "기장 길음": ("기장이 길",),
            "소재 얇음": ("소재가 얇",), "타이트함": ("타이트",),
            "허리 큼": ("허리가 커", "허리가 크"), "허리 작음": ("허리가 작",),
            "소매 짧음": ("소매가 짧",), "기장 짧음": ("기장이 짧",)}
# size_complaint_pct는 docs/CONTRACTS.md에 명시된 이 5개 카테고리만으로 계산합니다.
SIZE_COMPLAINT_LABELS = {"사이즈 큼", "사이즈 작음", "소매 길음", "기장 길음", "타이트함"}
NEGATION_AFTER = ("지 않", "지않", "지 못", "지못")


def _matched_without_negation(text, word):
    idx = text.find(word)
    if idx == -1:
        return False
    before = text[max(0, idx - 3):idx].rstrip()
    after = text[idx + len(word):idx + len(word) + 6]
    if before.endswith("안"):
        return False
    return not any(marker in after for marker in NEGATION_AFTER)


def _any_match(text, words):
    return any(_matched_without_negation(text, word) for word in words)


def _size_or_fit_comments(rows):
    size_comments, fit_comments = [], []
    for row in rows:
        text = row["content"]
        if any(word in text for word in ("사이즈", "소매", "기장", "허리")):
            size_comments.append(text)
        if any(word in text for word in ("핏", "타이트", "루즈", "품")):
            fit_comments.append(text)
    return size_comments, fit_comments


def _finalize(mode, rows, positive, negative, complaints):
    count = len(rows)
    size_comments, fit_comments = _size_or_fit_comments(rows)
    rate = lambda n: round(n / count * 100, 1) if count else None
    pos = rate(sum(row["rating"] >= 4 for row in rows))
    neg = rate(sum(row["rating"] <= 2 for row in rows))
    neutral = rate(sum(row["rating"] == 3 for row in rows))
    summary = (f"리뷰 {count}건 중 긍정 평점(4~5점)은 {pos}%입니다. "
               f"주요 주의 키워드는 {', '.join(key for key, _ in negative.most_common(3)) or '없음'}입니다."
               if count else "리뷰가 없어 분석할 수 없습니다. 실측 정보를 확인해 주세요.")
    return {"mode": mode, "count": count, "positive_pct": pos, "negative_pct": neg,
            "neutral_pct": neutral, "size_complaint_pct": rate(complaints),
            "positive_keywords": [{"keyword": k, "count": v} for k, v in positive.most_common(5)],
            "negative_keywords": [{"keyword": k, "count": v} for k, v in negative.most_common(5)],
            "size_comments": size_comments[:4], "fit_comments": fit_comments[:4], "summary": summary}


def analyze(reviews):
    """규칙 기반 baseline. API를 호출하지 않습니다."""
    rows = [dict(row) for row in reviews]
    positive, negative = Counter(), Counter()
    complaints = 0
    for row in rows:
        text = row["content"]
        row_negative_labels = set()
        for label, words in POSITIVE.items():
            if _any_match(text, words):
                positive[label] += 1
        for label, words in NEGATIVE.items():
            if _any_match(text, words):
                negative[label] += 1
                row_negative_labels.add(label)
        if row_negative_labels & SIZE_COMPLAINT_LABELS:
            complaints += 1
    return _finalize("rule-based-v2", rows, positive, negative, complaints)
