"""OpenAI 클라이언트 공통 예외. Streamlit을 import하지 않습니다."""


class LLMError(RuntimeError):
    """API 호출 실패. 호출부에서 error 로그로 남긴 뒤 그대로 전파합니다."""
