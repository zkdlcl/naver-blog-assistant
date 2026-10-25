from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import httpx

from core.config import AppConfig
from core.content_analyzer import ContentAnalysisRequest, ContentAnalysisResult


@dataclass(frozen=True)
class AiContentFeedback:
    provider: str
    model: str
    summary: str
    priority_actions: list[str]
    title_suggestions: list[str]
    opening_paragraph: str
    differentiation_point: str

    def to_dict(self) -> dict:
        return asdict(self)


class OpenAICompatibleContentAdvisor:
    def __init__(
        self,
        *,
        provider: str,
        api_key: str,
        model: str,
        base_url: str,
        app_url: str | None = None,
        app_name: str | None = None,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.app_url = app_url
        self.app_name = app_name
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    @classmethod
    def from_config(cls, config: AppConfig) -> OpenAICompatibleContentAdvisor | None:
        if not config.ai_enabled:
            return None
        return cls(
            provider=config.ai_provider,
            api_key=config.ai_api_key,
            model=config.ai_model,
            base_url=config.ai_base_url,
            app_name="BMS",
        )

    async def advise(
        self,
        request: ContentAnalysisRequest,
        result: ContentAnalysisResult,
    ) -> AiContentFeedback:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Korean blog writing editor. "
                        "Return only compact JSON. "
                        "Focus on useful blog-writing feedback, not policy boilerplate. "
                        "Do not mention search engine official scores. "
                        "Keep recommendations practical for one personal blogger."
                    ),
                },
                {
                    "role": "user",
                    "content": build_advisor_prompt(request, result),
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            if self.app_url:
                headers["HTTP-Referer"] = self.app_url
            if self.app_name:
                headers["X-Title"] = self.app_name

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        parsed = parse_json_object(content)

        return AiContentFeedback(
            provider=self.provider,
            model=self.model,
            summary=str(parsed.get("summary", "")).strip(),
            priority_actions=clean_text_list(parsed.get("priority_actions"), limit=3),
            title_suggestions=clean_text_list(parsed.get("title_suggestions"), limit=2),
            opening_paragraph=str(parsed.get("opening_paragraph", "")).strip(),
            differentiation_point=str(parsed.get("differentiation_point", "")).strip(),
        )


def build_advisor_prompt(
    request: ContentAnalysisRequest,
    result: ContentAnalysisResult,
) -> str:
    body = request.body.strip()
    if len(body) > 9000:
        body = f"{body[:9000]}\n...[truncated]"

    return f"""
다음은 네이버 블로그 초안 분석 데이터입니다.
작성자가 바로 수정할 수 있는 정보만 남겨 간결하게 정리해 주세요.

출력 규칙:
- 반드시 JSON 객체만 출력
- 한국어로 작성
- 문장은 짧고 실무형으로 작성
- priority_actions는 최대 3개
- title_suggestions는 최대 2개
- opening_paragraph는 2~4문장
- differentiation_point는 1문장

JSON schema:
{{
  "summary": "한두 문장 요약",
  "priority_actions": ["...", "..."],
  "title_suggestions": ["...", "..."],
  "opening_paragraph": "첫 문단 개선안",
  "differentiation_point": "이번 글을 어떻게 차별화할지"
}}

입력:
- 키워드: {request.keyword}
- 제목: {request.title}
- 본문:
{body}

현재 내부 분석 요약:
- 예상 의도: {result.intent}
- 총점: {result.score}
- 우선 수정 항목: {", ".join(result.priority_actions[:4]) or "없음"}
- 누락 항목: {", ".join(result.missing_topics[:5]) or "없음"}
- 위험 요소: {", ".join(result.risk_warnings[:3]) or "없음"}
- 사진 체크리스트: {", ".join(result.photo_checklist[:4]) or "없음"}
- 차별화 가이드: {", ".join(result.differentiation_guidance[:4]) or "없음"}
""".strip()


def parse_json_object(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start : end + 1]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("AI response is not a JSON object.")
    return parsed


def clean_text_list(value, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
        if len(items) >= limit:
            break
    return items
