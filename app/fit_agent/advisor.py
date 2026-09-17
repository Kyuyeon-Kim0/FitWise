"""OpenAI 기반 구매 권고 Agent. 점수 계산은 결정론적 분석 모듈에 남깁니다."""
import json

from app.config import get_settings


INSTRUCTIONS = """당신은 FitWise 구매 적합도 상담 Agent입니다.
제공된 데이터만 근거로 한국어 구매 권고를 작성하세요. 점수를 새로 계산하거나
반품 가능성을 단정하지 마세요. 신체 정보가 없으면 추측하지 마세요.
반드시 아래 JSON 객체만 반환하세요.
{
  "recommendation": "한두 문장의 구매 권고",
  "risk_signals": ["주의할 근거"],
  "next_actions": ["사용자가 할 다음 행동"],
  "explanation": "점수와 데이터에 근거한 짧은 설명"
}"""


def advise(product, size, preferred_fit, fit_result, review_result):
    """API 키가 설정된 경우에만 개인화된 자연어 권고를 생성합니다."""
    settings = get_settings()
    if not settings.api_key or not settings.model:
        return None

    # SDK를 여기서 import해, API를 사용하지 않는 baseline 실행은 의존성 오류 없이 동작합니다.
    from openai import OpenAI

    context = {
        "product": {"name": product["name"], "category": product["category"],
                    "description": product["description"], "measurements": product["measurements"]},
        "selected_size": size,
        "user_selected_preferred_fit": preferred_fit,
        "fit_score": fit_result["score"],
        "fit_label": fit_result["label"],
        "metrics": [{"label": metric["label"], "value": metric["value"],
                     "count": metric["count"], "returned": metric.get("returned")}
                    for metric in fit_result["metrics"]],
        "calculation_reasons": fit_result["reasons"],
        "review": {key: review_result[key] for key in
                   ("count", "positive_pct", "negative_pct", "size_complaint_pct",
                    "negative_keywords", "summary")},
    }
    response = OpenAI(api_key=settings.api_key).responses.create(
        model=settings.model,
        instructions=INSTRUCTIONS,
        input=json.dumps(context, ensure_ascii=False),
    )
    result = json.loads(response.output_text)
    required = {"recommendation", "risk_signals", "next_actions", "explanation"}
    if not required.issubset(result):
        raise ValueError("AI Agent 응답 형식이 올바르지 않습니다.")
    return {key: result[key] for key in required}
