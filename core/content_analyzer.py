from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field


CHECK_SEARCH_INTENT = "검색 의도 일치도"
CHECK_TITLE_INTRO = "제목/첫문단 명확성"
CHECK_READABILITY = "구조와 가독성"
CHECK_COVERAGE = "키워드/관련어 커버리지"
CHECK_TRUST = "경험/신뢰 요소"
CHECK_TOPIC_GAPS = "독자 기대 정보 누락"
CHECK_RISKS = "위험 요소"

CHECK_MAX_SCORES = {
    CHECK_SEARCH_INTENT: 20,
    CHECK_TITLE_INTRO: 15,
    CHECK_READABILITY: 15,
    CHECK_COVERAGE: 15,
    CHECK_TRUST: 15,
    CHECK_TOPIC_GAPS: 10,
    CHECK_RISKS: 10,
}

INTENT_TERMS = {
    "지역형": ("위치", "주소", "주차", "영업시간", "예약", "웨이팅", "메뉴", "가격", "가는법"),
    "후기형": ("후기", "방문", "내돈내산", "경험", "맛", "분위기", "장점", "단점", "추천"),
    "비교형": ("비교", "차이", "추천", "순위", "장단점", "가격", "선택", "대신"),
    "목록형": ("후보", "브랜드", "가격", "소재", "크기", "수납", "착용", "코디", "구매처"),
    "정보형": ("방법", "정리", "팁", "준비", "주의", "기간", "비용", "절차", "FAQ"),
}

EXPERIENCE_TERMS = (
    "방문",
    "직접",
    "제가",
    "저는",
    "먹어",
    "써보",
    "느낀",
    "사진",
    "영수증",
    "가격",
    "날짜",
    "예약",
    "대기",
    "장점",
    "단점",
    "주의",
)

RISK_TERMS = (
    "무조건",
    "100%",
    "완벽",
    "최고",
    "필수",
    "보장",
    "절대",
    "역대급",
    "충격",
    "대박",
)

SENSITIVE_TERMS = ("병원", "치료", "약", "보험", "대출", "투자", "법률", "소송", "세금")
TOPIC_STOP_WORDS = {
    "naver",
    "blog",
    "com",
    "https",
    "http",
    "www",
    "네이버",
    "블로그",
    "후기",
    "리뷰",
    "추천",
    "정리",
    "방문",
    "직접",
    "내돈내산",
    "그리고",
    "그래서",
    "이번",
    "오늘",
    "상위",
    "글",
    "정보",
    "ㅋㅋ",
    "ㅎㅎ",
    "ㅠㅠ",
    "ㅜㅜ",
    "같다",
    "같은",
    "같아서",
    "같기도",
    "같은데",
    "가능하다",
    "가운데",
    "가장",
    "가격도",
    "정도",
    "정말",
    "진짜",
    "살짝",
    "너무",
    "그리고",
    "그냥",
    "역시",
    "더욱",
    "조금",
    "많이",
    "바로",
    "사용",
    "제품",
    "후보",
    "가지",
    "같고",
    "같음",
    "갠적으로",
    "개인적으로",
    "겁나",
    "게시글의",
    "가져옴",
    "걸쳐도",
    "고급진",
    "그치만",
    "근데",
    "내가",
    "과하지",
    "완전",
    "약간",
    "뭔가",
    "무튼",
    "아주",
    "계속",
    "자꾸",
    "드디어",
    "첫번째",
    "두번째",
    "세번째",
    "네번째",
    "마지막",
    "출처",
    "입력",
    "활용",
    "설정",
    "설명을",
    "입력하세요",
}
TOPIC_ALIASES = {
    "위치": ("위치", "주소", "가는법", "찾아가는", "오시는"),
    "주소": ("주소", "위치", "가는법"),
    "주차": ("주차", "주차장", "발렛", "공영주차"),
    "영업시간": ("영업시간", "운영시간", "오픈", "마감", "휴무"),
    "예약": ("예약", "캐치테이블", "네이버예약", "전화예약"),
    "웨이팅": ("웨이팅", "대기", "줄서는", "대기시간"),
    "메뉴": ("메뉴", "대표메뉴", "메뉴판", "시그니처"),
    "가격": ("가격", "비용", "금액", "요금", "할인가"),
    "가는법": ("가는법", "위치", "주소", "역에서"),
    "후기": ("후기", "리뷰", "방문기"),
    "방문": ("방문", "다녀온", "갔다온"),
    "경험": ("경험", "직접", "느낀"),
    "맛": ("맛", "맛있", "풍미"),
    "분위기": ("분위기", "인테리어", "좌석", "공간"),
    "장점": ("장점", "좋았", "만족"),
    "단점": ("단점", "아쉬", "불편"),
    "비교": ("비교", "차이", "vs"),
    "차이": ("차이", "비교", "다른점"),
    "순위": ("순위", "랭킹", "베스트"),
    "선택": ("선택", "고르는", "기준"),
    "대신": ("대신", "대체", "비슷한"),
    "후보": ("후보", "위시리스트", "리스트", "모음"),
    "브랜드": ("브랜드", "미닛뮤트", "분크", "모노로우", "드래곤디퓨전"),
    "소재": ("소재", "가죽", "나일론", "캔버스", "코듀로이"),
    "크기": ("크기", "사이즈", "가로", "세로", "폭", "기장", "기장감", "길이", "루즈핏", "핏되는"),
    "수납": ("수납", "내부", "포켓", "공간"),
    "착용": ("착용", "착샷", "코디", "착장", "입었", "입고", "걸쳐", "숄더", "크로스", "백팩"),
    "코디": ("코디", "룩", "착장", "데일리"),
    "구매처": ("구매처", "구매링크", "공홈", "쇼룸", "매장", "온라인", "지그재그", "zigzag"),
    "방법": ("방법", "하는법", "절차"),
    "팁": ("팁", "노하우", "꿀팁"),
    "준비": ("준비", "준비물", "챙길"),
    "주의": ("주의", "주의점", "유의"),
    "기간": ("기간", "일정", "소요"),
    "비용": ("비용", "가격", "금액"),
    "절차": ("절차", "순서", "방법"),
    "FAQ": ("faq", "질문", "자주묻는"),
}

WORD_RE = re.compile(r"[\w가-힣]+", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"[.!?。！？\n]+")
EDITOR_MEDIA_MARKERS = (
    "AI 활용 설정",
    "출처 입력",
    "사진 설명을 입력하세요.",
    "동영상 설명을 입력하세요.",
)


@dataclass(frozen=True)
class ContentAnalysisRequest:
    keyword: str
    title: str
    body: str
    reference_posts: list["ReferencePost"] = field(default_factory=list)
    owner_posts: list["OwnerPostContext"] = field(default_factory=list)


@dataclass(frozen=True)
class ReferencePost:
    title: str
    summary: str = ""
    url: str = ""


@dataclass(frozen=True)
class OwnerPostContext:
    post_id: int
    title: str
    url: str
    category: str = ""
    published_at: str = ""
    content_summary: str = ""
    content_text: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ContentCheck:
    name: str
    score: int
    max_score: int
    suggestions: list[str]


@dataclass(frozen=True)
class ContentAnalysisResult:
    score: int
    summary: str
    score_label: str
    intent: str
    checks: list[ContentCheck]
    priority_actions: list[str]
    title_suggestions: list[str]
    heading_suggestions: list[str]
    risk_warnings: list[str]
    missing_topics: list[str]
    input_warnings: list[str]
    benchmark_notes: list[str]
    content_stats: dict[str, int]
    photo_checklist: list[str]
    differentiation_guidance: list[str]
    serp_missing_topic_candidates: list["SerpMissingTopicCandidate"]
    internal_link_candidates: list["InternalLinkCandidate"]
    existing_post_overlap_warnings: list["ExistingPostOverlapWarning"]


@dataclass(frozen=True)
class SerpMissingTopicCandidate:
    topic: str
    count: int
    matched_missing_topic: bool
    basis: str
    guidance: str


@dataclass(frozen=True)
class InternalLinkCandidate:
    post_id: int
    title: str
    url: str
    category: str
    published_at: str
    score: int
    reasons: list[str]
    guidance: str


@dataclass(frozen=True)
class ExistingPostMatch:
    post_id: int
    title: str
    url: str
    reason: str


@dataclass(frozen=True)
class ExistingPostOverlapWarning:
    topic: str
    overlap_type: str
    count: int
    matched_posts: list[ExistingPostMatch]
    guidance: str


def analyze_content(request: ContentAnalysisRequest) -> ContentAnalysisResult:
    title = normalize_space(request.title)
    keyword = derive_analysis_keyword(request.keyword, title)
    body, input_warnings, content_stats = normalize_pasted_body(request.body)
    if not keyword:
        raise ValueError("keyword must not be empty")
    if not title:
        raise ValueError("title must not be empty")
    if not body:
        raise ValueError("body must not be empty")

    text = f"{title}\n{body}"
    first_paragraph = first_non_empty_paragraph(body)
    intent = detect_intent(keyword, title, body)
    missing_topics = detect_missing_topics(intent, text)
    serp_missing_topic_candidates = detect_serp_missing_topic_candidates(
        keyword,
        intent,
        text,
        missing_topics,
        request.reference_posts,
    )
    internal_link_candidates = detect_internal_link_candidates(
        keyword,
        title,
        body,
        intent,
        request.owner_posts,
    )
    existing_post_overlap_warnings = detect_existing_post_overlap_warnings(
        keyword,
        title,
        body,
        request.owner_posts,
    )
    risk_warnings, risk_penalty = detect_risks(keyword, title, body)

    checks = [
        score_search_intent(keyword, title, body, intent),
        score_title_intro(keyword, title, first_paragraph),
        score_readability(body),
        score_coverage(keyword, text, intent),
        score_trust(body),
        score_topic_gaps(missing_topics),
        score_risks(risk_warnings, risk_penalty),
    ]
    total_score = sum(check.score for check in checks)
    priority_actions = build_priority_actions(checks, missing_topics, risk_warnings)

    return ContentAnalysisResult(
        score=total_score,
        summary=build_summary(total_score, priority_actions),
        score_label="네이버 공식 점수가 아닌 BMS 내부 프록시 점수입니다.",
        intent=intent,
        checks=checks,
        priority_actions=priority_actions,
        title_suggestions=build_title_suggestions(keyword, title, intent),
        heading_suggestions=build_heading_suggestions(keyword, intent, missing_topics),
        risk_warnings=risk_warnings,
        missing_topics=missing_topics,
        input_warnings=input_warnings,
        benchmark_notes=build_benchmark_notes(
            title,
            body,
            intent,
            risk_warnings,
            missing_topics,
            content_stats,
            serp_missing_topic_candidates,
            internal_link_candidates,
            existing_post_overlap_warnings,
        ),
        content_stats=content_stats,
        photo_checklist=build_photo_checklist(
            keyword,
            intent,
            body,
            content_stats,
            missing_topics,
        ),
        differentiation_guidance=build_differentiation_guidance(
            keyword,
            intent,
            missing_topics,
            serp_missing_topic_candidates,
            internal_link_candidates,
            existing_post_overlap_warnings,
        ),
        serp_missing_topic_candidates=serp_missing_topic_candidates,
        internal_link_candidates=internal_link_candidates,
        existing_post_overlap_warnings=existing_post_overlap_warnings,
    )


def content_analysis_to_dict(result: ContentAnalysisResult) -> dict:
    return asdict(result)


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def derive_analysis_keyword(keyword: str, title: str = "") -> str:
    normalized = normalize_space(keyword)
    if not normalized:
        return ""

    hashtag_tokens = re.findall(r"#([^\s#]+)", normalized)
    without_hashtags = normalize_space(re.sub(r"(?:^|\s)#[^\s#]+", " ", normalized))
    candidate = without_hashtags or " ".join(clean_hashtag_token(token) for token in hashtag_tokens[:3])
    candidate = cleanup_keyword_phrase(candidate)

    if not candidate and title:
        candidate = cleanup_keyword_phrase(title)
    if not candidate:
        candidate = normalized

    return candidate[:40].strip()


def clean_hashtag_token(token: str) -> str:
    token = re.sub(r"추천$", "", token.strip())
    token = re.sub(r"위시리스트$", "", token)
    return token or token.strip()


def cleanup_keyword_phrase(value: str) -> str:
    phrase = normalize_space(value)
    phrase = re.sub(r"\[[^\]]+\]", " ", phrase)
    phrase = re.sub(r"#\S+", " ", phrase)
    phrase = normalize_space(phrase)
    phrase = re.split(r"\s*(?:::|ㅣ|\||feat\.?|FEAT\.?|,)\s*", phrase)[0]
    phrase = re.sub(r"\s+", " ", phrase).strip(" -_/·")
    return phrase


def normalize_pasted_body(value: str) -> tuple[str, list[str], dict[str, int]]:
    warnings = []
    original = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    lines = [normalize_pasted_line(line) for line in original.split("\n")]
    estimated_photo_count = estimate_photo_count(lines)
    lines, map_place_count = normalize_naver_map_lines(lines)

    compacted: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line
        if is_blank and previous_blank:
            continue
        compacted.append(line)
        previous_blank = is_blank

    normalized = "\n".join(compacted).strip()
    if estimated_photo_count > 0:
        warnings.append(f"사진 자리로 추정되는 긴 빈 줄 {estimated_photo_count}개를 분석 전에 한 줄 간격으로 정리했습니다.")
    if map_place_count > 0:
        warnings.append(f"네이버 지도 붙여넣기 문구 {map_place_count}개를 정리하고 장소명/주소는 보존했습니다.")

    return normalized, warnings, {
        "estimated_photo_count": estimated_photo_count,
        "map_place_count": map_place_count,
        "line_count": sum(1 for line in compacted if line),
    }


def normalize_pasted_line(line: str) -> str:
    line = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", line)
    return re.sub(r"[ \u00a0]+", " ", line).strip()


def estimate_photo_count(lines: list[str]) -> int:
    count = 0
    blank_run = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        if is_editor_media_marker(line):
            count += 1
            blank_run = 0
            index += 1
            while index < len(lines) and is_editor_media_marker(lines[index]):
                index += 1
            continue

        if not line:
            blank_run += 1
            index += 1
            continue

        if blank_run >= 2:
            count += 1
        blank_run = 0
        index += 1

    if blank_run >= 2:
        count += 1

    return count


def normalize_naver_map_lines(lines: list[str]) -> tuple[list[str], int]:
    cleaned = []
    map_place_count = 0
    index = 0

    while index < len(lines):
        line = lines[index]
        if is_editor_media_marker(line):
            index += 1
            continue
        if is_naver_map_marker(line, lines[index : index + 5]):
            place = line.removeprefix("위치").strip()
            distance_index = index + 1
            copyright_index = index + 2
            place_index = index + 3
            address_index = index + 4
            if place:
                cleaned.append(place)
            if address_index < len(lines) and is_probable_korean_address(lines[address_index]):
                cleaned.append(lines[address_index])
            elif place_index < len(lines) and lines[place_index] and lines[place_index] != place:
                cleaned.append(lines[place_index])

            map_place_count += 1
            index = max(address_index + 1, copyright_index + 1, distance_index + 1)
            continue

        if line == "© NAVER Corp." or re.fullmatch(r"\d+\s*m", line, flags=re.IGNORECASE):
            index += 1
            continue

        cleaned.append(line)
        index += 1

    return cleaned, map_place_count


def is_naver_map_marker(line: str, window: list[str]) -> bool:
    if not line.startswith("위치") or len(line) <= 2:
        return False
    has_distance = any(re.fullmatch(r"\d+\s*m", item, flags=re.IGNORECASE) for item in window[1:3])
    has_copyright = any(item == "© NAVER Corp." for item in window[1:4])
    return has_distance and has_copyright


def is_probable_korean_address(line: str) -> bool:
    return bool(re.search(r"(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|전라|경상|제주|북도|남도|특별시|광역시|시\s|군\s|구\s|읍\s|면\s|로\s|길\s)", line))


def is_editor_media_marker(line: str) -> bool:
    return line in EDITOR_MEDIA_MARKERS


def first_non_empty_paragraph(body: str) -> str:
    for paragraph in re.split(r"\n\s*\n|\r\n\s*\r\n", body):
        normalized = normalize_space(paragraph)
        if normalized:
            return normalized
    return normalize_space(body)


def tokenize(value: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(value)]


def split_sentences(value: str) -> list[str]:
    return [normalize_space(sentence) for sentence in SENTENCE_SPLIT_RE.split(value) if normalize_space(sentence)]


def contains_any(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    return any(term.lower() in text.lower() for term in terms)


def has_first_person_experience(text: str) -> bool:
    return contains_any(
        text,
        (
            "다녀왔",
            "방문했",
            "우리는",
            "우린",
            "저는",
            "제가",
            "직접",
            "먹었",
            "봤",
            "찍었",
            "느꼈",
            "추천하고 싶",
        ),
    )


def has_cost_evidence(text: str) -> bool:
    return bool(
        re.search(r"(?:\d{1,3}(?:,\d{3})+|\d+\s*원|₩\s*\d+)", text)
        or contains_any(text, ("입장료", "이용요금", "가격", "비용", "요금", "할인", "예약"))
    )


def has_downside_signal(text: str) -> bool:
    return contains_any(
        text,
        (
            "단점",
            "아쉬",
            "불편",
            "주의",
            "다만",
            "만차",
            "붐비",
            "흐렸",
            "soso",
            "쏘쏘",
            "보통",
        ),
    )


def detect_intent(keyword: str, title: str, body: str) -> str:
    combined = f"{keyword} {title} {body[:500]}".lower()
    scores = {intent: 0 for intent in INTENT_TERMS}

    location_markers = ("카페", "맛집", "숙소", "여행", "서촌", "성수", "홍대", "강남", "제주", "부산", "근처")
    if contains_any(combined, location_markers):
        scores["지역형"] += 2
    if contains_any(combined, ("후기", "리뷰", "내돈내산", "방문")):
        scores["후기형"] += 2
    if contains_any(combined, ("위시리스트", "쇼핑리스트", "리스트", "모음", "컬렉션")):
        scores["목록형"] += 4
    if contains_any(combined, ("비교", "순위", "vs", "차이")):
        scores["비교형"] += 2
    if contains_any(combined, ("방법", "정리", "팁", "가이드", "체크리스트")):
        scores["정보형"] += 2

    for intent, terms in INTENT_TERMS.items():
        scores[intent] += sum(1 for term in terms if term.lower() in combined)

    return max(scores.items(), key=lambda item: (item[1], item[0]))[0]


def score_search_intent(keyword: str, title: str, body: str, intent: str) -> ContentCheck:
    text = f"{title} {body}".lower()
    terms = relevant_intent_terms(intent, text)
    matched = [term for term in terms if topic_present(term, text)]
    score = 9 + min(7, len(matched) * 2)
    if keyword_matches_text(keyword, text):
        score += 2
    if len(body) >= 500:
        score += 2
    elif len(body) >= 300:
        score += 1

    suggestions = []
    if len(matched) < 3:
        suggestions.append(f"{intent} 키워드에서 독자가 기대하는 {', '.join(terms[:4])} 정보를 보강하세요.")
    if len(body) < 500:
        suggestions.append("본문이 짧습니다. 실제 상황, 선택 이유, 확인 정보를 더 적어주세요.")

    return make_check(CHECK_SEARCH_INTENT, min(score, CHECK_MAX_SCORES[CHECK_SEARCH_INTENT]), suggestions)


def score_title_intro(keyword: str, title: str, first_paragraph: str) -> ContentCheck:
    score = 5
    suggestions = []
    if keyword_matches_text(keyword, title):
        score += 5
    else:
        suggestions.append("제목에 타깃 키워드를 자연스럽게 포함하세요.")

    if keyword_matches_text(keyword, first_paragraph):
        score += 3
    else:
        suggestions.append("첫 문단에 키워드와 글의 결론을 한 번에 보여주세요.")

    if 14 <= len(title) <= 55:
        score += 2
    else:
        suggestions.append("제목은 너무 짧거나 길지 않게 핵심 정보 중심으로 다듬으세요.")

    if contains_any(first_paragraph, ("결론", "추천", "좋았", "아쉬", "이유", "방문", "정리")):
        score += 1
    else:
        suggestions.append("첫 문단에 방문 목적, 판단 기준, 결론 중 하나를 넣으세요.")

    return make_check(CHECK_TITLE_INTRO, min(score, CHECK_MAX_SCORES[CHECK_TITLE_INTRO]), suggestions)


def score_readability(body: str) -> ContentCheck:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    sentences = split_sentences(body)
    avg_sentence_len = sum(len(sentence) for sentence in sentences) / max(len(sentences), 1)
    heading_count = sum(1 for line in lines if is_heading_like(line))
    list_count = sum(1 for line in lines if line.startswith(("-", "*", "1.", "2.", "3.")))

    score = 6
    suggestions = []
    if len(lines) >= 4:
        score += 2
    else:
        suggestions.append("본문을 여러 문단으로 나눠 모바일에서 읽기 쉽게 만드세요.")
    if heading_count >= 2:
        score += 4
    elif heading_count == 1:
        score += 2
    else:
        suggestions.append("정보 묶음별 소제목을 2개 이상 추가하세요.")
    if avg_sentence_len <= 85:
        score += 2
    else:
        suggestions.append("긴 문장을 나눠 핵심 판단이 빨리 보이게 하세요.")
    if list_count > 0 or contains_any(body, ("정리", "요약", "FAQ", "체크")):
        score += 2
    else:
        suggestions.append("가격, 장단점, 준비물처럼 비교하기 쉬운 정보는 목록으로 정리하세요.")

    return make_check(CHECK_READABILITY, min(score, CHECK_MAX_SCORES[CHECK_READABILITY]), suggestions)


def score_coverage(keyword: str, text: str, intent: str) -> ContentCheck:
    tokens = tokenize(text)
    keyword_parts = [part for part in tokenize(keyword) if len(part) >= 2]
    keyword_hits = sum(tokens.count(part) for part in keyword_parts)
    density = keyword_hits / max(len(tokens), 1)
    related_terms = relevant_intent_terms(intent, text)
    related_matches = [term for term in related_terms if topic_present(term, text)]

    score = 5 + min(5, len(related_matches))
    suggestions = []
    if keyword_matches_text(keyword, text):
        score += 3
    else:
        suggestions.append("키워드의 핵심 단어가 제목과 본문에 자연스럽게 모두 들어가게 하세요.")

    if 0.005 <= density <= 0.06:
        score += 2
    elif density > 0.06:
        suggestions.append("키워드 반복이 많아 보입니다. 같은 말을 줄이고 구체 정보로 대체하세요.")
    else:
        suggestions.append("키워드가 거의 보이지 않습니다. 문맥에 맞는 위치에 자연스럽게 추가하세요.")

    if len(related_matches) < 4:
        suggestions.append(f"관련 정보 후보를 보강하세요: {', '.join(related_terms[:5])}.")

    return make_check(CHECK_COVERAGE, min(score, CHECK_MAX_SCORES[CHECK_COVERAGE]), suggestions)


def score_trust(body: str) -> ContentCheck:
    matched = [term for term in EXPERIENCE_TERMS if term.lower() in body.lower()]
    score = 5 + min(6, len(matched))
    suggestions = []

    if has_first_person_experience(body):
        score += 1

    if contains_any(body, ("202", "최근", "이번", "지난", "오늘")):
        score += 1
    else:
        suggestions.append("방문일, 기준일, 최근 확인 여부를 넣어 정보의 시점을 밝혀주세요.")

    if has_cost_evidence(body):
        score += 1

    if has_downside_signal(body):
        score += 2
    else:
        suggestions.append("좋았던 점뿐 아니라 아쉬운 점이나 주의할 점도 적어 신뢰감을 높이세요.")

    if len(matched) < 5 and not (has_first_person_experience(body) and has_cost_evidence(body)):
        suggestions.append("직접 경험, 사진 설명, 가격, 예약/대기 같은 확인 가능한 근거를 보강하세요.")

    return make_check(CHECK_TRUST, min(score, CHECK_MAX_SCORES[CHECK_TRUST]), suggestions)


def relevant_intent_terms(intent: str, text: str) -> tuple[str, ...]:
    terms = list(INTENT_TERMS[intent])
    if intent == "후기형":
        terms = [term for term in terms if term not in {"후기", "방문", "추천"}]
        if not contains_any(text, ("맛집", "카페", "식당", "메뉴", "커피", "디저트", "음식", "먹거리", "먹었")):
            terms = [term for term in terms if term != "맛"]
    if intent == "목록형":
        terms = [term for term in terms if term != "후보"]
        if is_clothing_context(text) and not is_bag_context(text):
            terms = [term for term in terms if term != "수납"]
    return tuple(terms)


def is_clothing_context(text: str) -> bool:
    return contains_any(
        text,
        (
            "셔츠",
            "블라우스",
            "니트",
            "가디건",
            "원피스",
            "치마",
            "스커트",
            "팬츠",
            "데님",
            "나시",
            "하객룩",
            "출근룩",
            "착장",
            "코디",
        ),
    )


def is_bag_context(text: str) -> bool:
    return contains_any(text, ("가방", "백팩", "숄더백", "토트백", "크로스백", "미니백", "수납"))


def topic_present(topic: str, text: str) -> bool:
    lower_text = text.lower()
    if topic == "내돈내산":
        return "내돈내산" in lower_text or (has_first_person_experience(text) and has_cost_evidence(text))
    if topic == "경험":
        return has_first_person_experience(text) or contains_any(text, ("경험", "사진", "후기", "리뷰"))
    if topic == "단점":
        return has_downside_signal(text)
    if topic == "가격" and re.search(r"(?:\d{1,3}(?:,\d{3})+|\d+\s*원|₩\s*\d+)", lower_text):
        return True
    if topic == "구매처" and re.search(r"(?:s\.zigzag\.kr|zigzag|지그재그|구매\s*링크)", lower_text):
        return True

    aliases = TOPIC_ALIASES.get(topic, (topic,))
    return any(alias.lower() in lower_text for alias in aliases)


def keyword_matches_text(keyword: str, text: str) -> bool:
    keyword_norm = normalize_space(keyword).lower()
    text_norm = normalize_space(text).lower()
    if not keyword_norm:
        return False
    if keyword_norm in text_norm:
        return True

    signals = keyword_signal_tokens(keyword_norm)
    if not signals:
        return False
    text_tokens = tokenize(text_norm)
    matched = [
        token
        for token in signals
        if token in text_norm
        or any(token in text_token or text_token in token for text_token in text_tokens if len(text_token) >= 2)
    ]
    return len(matched) >= max(1, min(len(signals), 3) - 1)


def keyword_signal_tokens(keyword: str) -> list[str]:
    signals: list[str] = []
    fashion_suffixes = (
        "셔츠",
        "블라우스",
        "가디건",
        "니트",
        "원피스",
        "스커트",
        "팬츠",
        "가방",
        "백팩",
        "숄더백",
    )
    for token in tokenize(keyword):
        if is_noise_token(token):
            continue
        signals.append(token)
        for suffix in fashion_suffixes:
            if token.endswith(suffix) and token != suffix:
                prefix = token[: -len(suffix)]
                if len(prefix) >= 2:
                    signals.append(prefix)
                signals.append(suffix)
    return dedupe_keep_order(signals)


def detect_missing_topics(intent: str, text: str) -> list[str]:
    terms = relevant_intent_terms(intent, text)
    missing = [term for term in terms if not topic_present(term, text)]
    return missing[:5]


def detect_serp_missing_topic_candidates(
    keyword: str,
    intent: str,
    own_text: str,
    missing_topics: list[str],
    reference_posts: list[ReferencePost],
) -> list[SerpMissingTopicCandidate]:
    posts = dedupe_reference_posts(reference_posts)
    if not posts:
        return []

    topic_terms = dedupe_keep_order(
        list(relevant_intent_terms(intent, own_text))
        + [term for terms in INTENT_TERMS.values() for term in terms if term != "후보"]
    )
    topic_counts: Counter[str] = Counter()
    for post in posts:
        post_text = normalize_space(f"{post.title} {post.summary}")
        if not post_text:
            continue
        lower_text = post_text.lower()
        for topic in topic_terms:
            if topic_present(topic, lower_text):
                topic_counts[topic] += 1

    missing_set = set(missing_topics)
    candidates: list[SerpMissingTopicCandidate] = []
    for topic, count in topic_counts.items():
        # Keep SERP hints only when the topic repeats across reference posts.
        # Single-post mentions add noise even if the current draft also misses them.
        if count < 2:
            continue
        if topic_present(topic, own_text) and topic not in missing_set:
            continue
        candidates.append(make_serp_candidate(topic, count, topic in missing_set))

    candidates.sort(key=lambda item: (not item.matched_missing_topic, -item.count, item.topic))
    return candidates[:5]


def dedupe_reference_posts(posts: list[ReferencePost]) -> list[ReferencePost]:
    seen: set[str] = set()
    results: list[ReferencePost] = []
    for post in posts:
        key = post.url.strip() or normalize_space(post.title).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(post)
    return results


def make_serp_candidate(topic: str, count: int, matched_missing_topic: bool) -> SerpMissingTopicCandidate:
    return SerpMissingTopicCandidate(
        topic=topic,
        count=count,
        matched_missing_topic=matched_missing_topic,
        basis="상위글 제목/요약에서 반복 확인",
        guidance="상위글을 베끼기 위한 자료가 아니라 독자 기대 정보 확인용 후보입니다.",
    )


def detect_internal_link_candidates(
    keyword: str,
    title: str,
    body: str,
    intent: str,
    owner_posts: list[OwnerPostContext],
) -> list[InternalLinkCandidate]:
    draft_text = f"{keyword} {title} {body}"
    keyword_parts = significant_tokens(keyword)
    intent_terms = set(INTENT_TERMS[intent])
    candidates: list[InternalLinkCandidate] = []

    for post in dedupe_owner_posts(owner_posts):
        post_text = owner_post_text(post)
        if not post_text:
            continue

        post_tokens = significant_tokens(post_text)
        shared_keyword_parts = sorted(keyword_parts & post_tokens)
        keyword_matches = [
            item
            for item in post.keywords
            if keyword_related(keyword, item)
        ]
        shared_intent_terms = [
            term
            for term in intent_terms
            if term.lower() in body.lower() and term.lower() in post_text.lower()
        ]

        score = 0
        reasons = []
        if shared_keyword_parts:
            score += min(4, len(shared_keyword_parts) * 2)
            reasons.append(f"핵심어 일치: {', '.join(shared_keyword_parts[:3])}")
        if keyword_matches:
            score += 3
            reasons.append(f"기존 목표 키워드 관련: {', '.join(keyword_matches[:2])}")
        if shared_intent_terms:
            score += min(2, len(shared_intent_terms))
            reasons.append(f"본문 정보 연결: {', '.join(shared_intent_terms[:2])}")

        has_specific_signal = bool(shared_keyword_parts or keyword_matches)
        if score < 5 or not has_specific_signal:
            continue

        candidates.append(
            InternalLinkCandidate(
                post_id=post.post_id,
                title=post.title,
                url=post.url,
                category=post.category,
                published_at=post.published_at,
                score=score,
                reasons=dedupe_keep_order(reasons)[:2],
                guidance="같은 주제를 반복하기보다, 이미 설명한 정보는 이 글로 넘기고 이번 글의 핵심 판단만 남기세요.",
            )
        )

    candidates.sort(key=lambda item: (-item.score, item.title))
    return candidates[:5]


def detect_existing_post_overlap_warnings(
    keyword: str,
    title: str,
    body: str,
    owner_posts: list[OwnerPostContext],
) -> list[ExistingPostOverlapWarning]:
    posts = dedupe_owner_posts(owner_posts)
    if not posts:
        return []

    exact_matches: list[ExistingPostMatch] = []
    similar_matches: list[ExistingPostMatch] = []
    topic_matches: list[tuple[int, ExistingPostMatch]] = []
    draft_text = f"{keyword} {title} {body}"
    draft_tokens = significant_tokens(draft_text)
    keyword_parts = significant_tokens(keyword)

    for post in posts:
        post_keywords = [item.strip() for item in post.keywords if item.strip()]
        normalized_post_keywords = {normalize_space(item).lower() for item in post_keywords}
        post_text = owner_post_text(post)
        post_tokens = significant_tokens(post_text)
        shared_tokens = sorted((draft_tokens & post_tokens) - keyword_parts)

        if normalize_space(keyword).lower() in normalized_post_keywords:
            exact_matches.append(
                ExistingPostMatch(
                    post_id=post.post_id,
                    title=post.title,
                    url=post.url,
                    reason="기존 목표 키워드와 일치",
                )
            )
            continue

        similar_keyword = next((item for item in post_keywords if keyword_related(keyword, item)), "")
        if similar_keyword:
            similar_matches.append(
                ExistingPostMatch(
                    post_id=post.post_id,
                    title=post.title,
                    url=post.url,
                    reason=f"유사 목표 키워드 사용: {similar_keyword}",
                )
            )
            continue

        if len(shared_tokens) >= 8:
            topic_matches.append(
                (
                    len(shared_tokens),
                    ExistingPostMatch(
                        post_id=post.post_id,
                        title=post.title,
                        url=post.url,
                        reason=f"본문/제목 주제어 겹침: {', '.join(shared_tokens[:5])}",
                    ),
                )
            )

    warnings: list[ExistingPostOverlapWarning] = []
    if exact_matches:
        warnings.append(
            make_overlap_warning(
                topic=keyword,
                overlap_type="target_keyword",
                matches=exact_matches,
            )
        )
    if similar_matches:
        warnings.append(
            make_overlap_warning(
                topic=keyword,
                overlap_type="similar_keyword",
                matches=similar_matches,
            )
        )
    if 0 < len(topic_matches) <= 30:
        topic_matches.sort(key=lambda item: (-item[0], item[1].title))
        warnings.append(
            make_overlap_warning(
                topic="본문 주제",
                overlap_type="topic_overlap",
                matches=[item[1] for item in topic_matches[:5]],
            )
        )

    return warnings[:3]


def make_overlap_warning(
    *,
    topic: str,
    overlap_type: str,
    matches: list[ExistingPostMatch],
) -> ExistingPostOverlapWarning:
    guidance = {
        "target_keyword": "이미 같은 목표 키워드 글이 있습니다. 새 글은 다른 방문 목적, 최신 정보, 비교 기준을 명확히 하세요.",
        "similar_keyword": "유사 키워드 글과 검색 의도가 겹칠 수 있습니다. 제목과 첫 문단에서 차별점을 먼저 보여주세요.",
        "topic_overlap": "기존 글과 다루는 정보가 많이 겹칩니다. 내부 링크로 넘길 정보와 새로 쓸 정보를 분리하세요.",
    }.get(overlap_type, "기존 글과 겹치는 부분을 확인하고 새 글의 차별점을 분명히 하세요.")

    return ExistingPostOverlapWarning(
        topic=topic,
        overlap_type=overlap_type,
        count=len(matches),
        matched_posts=matches[:5],
        guidance=guidance,
    )


def dedupe_owner_posts(posts: list[OwnerPostContext]) -> list[OwnerPostContext]:
    seen: set[str] = set()
    results: list[OwnerPostContext] = []
    for post in posts:
        key = post.url.strip() or str(post.post_id)
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(post)
    return results


def owner_post_text(post: OwnerPostContext) -> str:
    return normalize_space(
        " ".join(
            [
                post.title,
                post.category,
                post.content_summary,
                post.content_text[:3000],
                " ".join(post.keywords),
            ]
        )
    )


def significant_tokens(value: str) -> set[str]:
    return {
        token
        for token in tokenize(value)
        if not is_noise_token(token)
    }


def is_noise_token(token: str) -> bool:
    token = token.lower().strip()
    if len(token) < 2:
        return True
    if token in TOPIC_STOP_WORDS:
        return True
    if token.isdigit():
        return True
    if re.fullmatch(r"\d+[가-힣a-z]*", token):
        return True
    if re.fullmatch(r"[a-z]+", token):
        return True
    if re.fullmatch(r"[ㅋㅎㅠㅜ]+", token):
        return True
    if token.endswith(("하다", "했다", "합니다", "해서", "하고", "되는", "되어", "있는", "있고")):
        return True
    return False


def keyword_related(first: str, second: str) -> bool:
    first_norm = normalize_space(first).lower()
    second_norm = normalize_space(second).lower()
    if not first_norm or not second_norm:
        return False
    if first_norm == second_norm:
        return True

    first_tokens = significant_tokens(first_norm)
    second_tokens = significant_tokens(second_norm)
    if not first_tokens or not second_tokens:
        return False

    shared = first_tokens & second_tokens
    return len(shared) >= min(len(first_tokens), len(second_tokens), 2)


def score_topic_gaps(missing_topics: list[str]) -> ContentCheck:
    score = max(0, 10 - len(missing_topics) * 2)
    suggestions = []
    if missing_topics:
        suggestions.append(f"이 키워드에서 빠지기 쉬운 정보를 확인하세요: {', '.join(missing_topics)}.")
    return make_check(CHECK_TOPIC_GAPS, score, suggestions)


def detect_risks(keyword: str, title: str, body: str) -> tuple[list[str], int]:
    warnings = []
    text = f"{title}\n{body}"
    tokens = tokenize(text)
    keyword_parts = [part for part in tokenize(keyword) if len(part) >= 2]
    keyword_hits = sum(tokens.count(part) for part in keyword_parts)
    density = keyword_hits / max(len(tokens), 1)
    penalty = 0

    if density > 0.08:
        warnings.append("키워드 반복 비율이 높습니다. 도배처럼 보이지 않게 표현을 줄이세요.")
        penalty += 3

    risky_terms = [term for term in RISK_TERMS if term.lower() in text.lower()]
    if risky_terms:
        warnings.append(f"과장 또는 단정 표현을 줄이세요: {', '.join(risky_terms[:4])}.")
        penalty += min(3, len(risky_terms))

    duplicated = duplicated_sentences(body)
    if duplicated:
        warnings.append("반복 문장이 보입니다. 같은 문장을 줄이고 새 정보로 바꾸세요.")
        penalty += 2

    if len(body) < 350:
        warnings.append("본문이 짧아 실제 경험과 판단 근거가 부족해 보일 수 있습니다.")
        penalty += 2

    if contains_any(text, SENSITIVE_TERMS) and contains_any(text, ("보장", "완치", "수익", "확실")):
        warnings.append("민감 주제에서 보장/확신 표현은 피하고 개인 경험 범위를 명확히 하세요.")
        penalty += 3

    return warnings, penalty


def score_risks(warnings: list[str], penalty: int) -> ContentCheck:
    suggestions = warnings[:]
    if not suggestions:
        suggestions.append("큰 위험 신호는 보이지 않습니다. 그래도 과장 표현과 반복은 발행 전 한 번 더 확인하세요.")
    return make_check(CHECK_RISKS, max(0, 10 - penalty), suggestions)


def build_priority_actions(
    checks: list[ContentCheck],
    missing_topics: list[str],
    risk_warnings: list[str],
) -> list[str]:
    actions = []
    for check in sorted(checks, key=lambda item: item.score / item.max_score):
        actions.extend(check.suggestions[:1])
        if len(actions) >= 3:
            break

    if missing_topics and len(actions) < 4:
        actions.append(f"누락 가능성이 큰 항목부터 보강하세요: {', '.join(missing_topics[:3])}.")
    if risk_warnings and len(actions) < 4:
        actions.append(risk_warnings[0])

    return dedupe_keep_order(actions)[:4]


def build_summary(score: int, priority_actions: list[str]) -> str:
    if score >= 85:
        base = "발행 전 최종 점검 단계입니다."
    elif score >= 70:
        base = "기본기는 갖췄고 몇 가지 보강이 필요합니다."
    elif score >= 50:
        base = "독자가 기대하는 핵심 정보가 아직 부족합니다."
    else:
        base = "제목, 첫 문단, 구조부터 다시 잡는 편이 좋습니다."

    if priority_actions:
        return f"{base} 가장 먼저 할 일은 {priority_actions[0]}"
    return base


def build_title_suggestions(keyword: str, title: str, intent: str) -> list[str]:
    suffixes = {
        "지역형": ["위치와 주차까지 정리", "방문 전 알아둘 점", "메뉴와 분위기 후기"],
        "후기형": ["직접 다녀온 후기", "좋았던 점과 아쉬운 점", "방문 전 체크할 것"],
        "비교형": ["선택 기준 정리", "장단점 비교", "추천 대상별 정리"],
        "목록형": ["위시리스트 정리", "브랜드별 후보", "구매 전 체크할 점"],
        "정보형": ["핵심만 정리", "처음 볼 때 알아둘 점", "체크리스트"],
    }
    keyword_label = choose_keyword_label(keyword, title)
    cleaned_title = cleanup_keyword_phrase(title) or title
    suggestions = [f"{keyword_label} {suffix}" for suffix in suffixes[intent]]
    if keyword_matches_text(keyword, cleaned_title):
        suggestions.insert(0, cleaned_title)
    elif keyword_matches_text(keyword, title):
        suggestions.insert(0, title)
    elif keyword_label and not title.lower().startswith(keyword_label.lower()):
        suggestions.insert(0, f"{keyword_label} {title}")
    else:
        suggestions.insert(0, title)
    return dedupe_keep_order(suggestions)[:3]


def build_heading_suggestions(keyword: str, intent: str, missing_topics: list[str]) -> list[str]:
    keyword_label = choose_keyword_label(keyword, keyword)
    headings = [f"{keyword_label} 한눈에 정리"]
    headings.extend(topic_to_heading(topic) for topic in missing_topics[:3])
    if intent == "후기형":
        headings.append("좋았던 점과 아쉬운 점")
    elif intent == "비교형":
        headings.append("어떤 사람에게 맞는지")
    elif intent == "목록형":
        headings.append("후보별 고른 이유")
    elif intent == "지역형":
        headings.append("방문 전 체크할 것")
    else:
        headings.append("자주 묻는 질문")
    return dedupe_keep_order(headings)[:5]


def choose_keyword_label(keyword: str, title: str) -> str:
    candidates = [cleanup_keyword_phrase(keyword), cleanup_keyword_phrase(title)]
    for candidate in candidates:
        label = compress_keyword_label(candidate)
        if label:
            return label
    return normalize_space(keyword)


def compress_keyword_label(value: str) -> str:
    raw_tokens = [token for token in WORD_RE.findall(value) if len(token) >= 2]
    tokens: list[str] = []
    for token in raw_tokens:
        if any(token == existing or token in existing or existing in token for existing in tokens):
            continue
        tokens.append(token)
    return " ".join(tokens[:4]).strip()


def topic_to_heading(topic: str) -> str:
    mapping = {
        "내돈내산": "비용과 할인 정리",
        "경험": "직접 경험 정리",
        "단점": "좋았던 점과 아쉬운 점",
        "장점": "좋았던 점 정리",
        "가격": "요금과 할인 정리",
        "주차": "주차와 입구 동선",
        "웨이팅": "혼잡도와 대기 팁",
        "영업시간": "운영시간과 입장 마감",
    }
    return mapping.get(topic, f"{topic} 정리")


def build_benchmark_notes(
    title: str,
    body: str,
    intent: str,
    risk_warnings: list[str],
    missing_topics: list[str],
    content_stats: dict[str, int],
    serp_missing_topic_candidates: list[SerpMissingTopicCandidate],
    internal_link_candidates: list[InternalLinkCandidate],
    existing_post_overlap_warnings: list[ExistingPostOverlapWarning],
) -> list[str]:
    notes = []
    estimated_photo_count = content_stats.get("estimated_photo_count", 0)
    if len(title) <= 45:
        notes.append("공개 SEO 가이드 관점: 제목은 주제를 정확히 드러내고 과하게 길지 않은 편이 좋습니다.")
    else:
        notes.append("공개 SEO 가이드 관점: 제목이 길면 핵심 주제가 흐려질 수 있어 압축을 권합니다.")

    if estimated_photo_count >= 3:
        notes.append(f"사진 흐름 점검: 붙여넣기 공백 기준 사진 약 {estimated_photo_count}개로 추정됩니다. 각 사진 앞뒤에 무엇을 봐야 하는지 한 줄씩 설명하세요.")
    elif estimated_photo_count > 0:
        notes.append(f"사진 흐름 점검: 붙여넣기 공백 기준 사진 약 {estimated_photo_count}개로 추정됩니다. 방문/후기 글이라면 핵심 장면이 충분한지 확인하세요.")
    elif contains_any(body, ("사진", "이미지", "메뉴판", "외관", "내부", "영수증")):
        notes.append("실무 벤치마크: 사진 언급이 있습니다. 각 사진 주변에 무엇을 확인해야 하는지 짧게 설명하는 흐름이 좋습니다.")
    else:
        notes.append("실무 벤치마크: 네이버 블로그 글은 사진 맥락이 중요한 편이라 외관, 메뉴판, 현장 사진 설명을 점검하세요.")

    if missing_topics:
        notes.append(f"독자 기대 정보 점검: {intent} 글에서 빠지기 쉬운 {', '.join(missing_topics[:3])} 항목을 확인하세요.")

    if serp_missing_topic_candidates:
        matched = [candidate.topic for candidate in serp_missing_topic_candidates if candidate.matched_missing_topic]
        if matched:
            notes.append(f"상위글 제목/요약 점검: {', '.join(matched[:3])} 항목은 검색 결과에서도 반복되어 독자 기대 정보로 확인할 만합니다.")

    if internal_link_candidates:
        notes.append(f"내 글 연결 점검: 관련 기존 글 {len(internal_link_candidates)}개가 있습니다. 독자 흐름에 맞는 글만 자연스럽게 연결하세요.")

    if existing_post_overlap_warnings:
        notes.append("기존 글 중복 점검: 같은 키워드나 비슷한 주제 글이 있어 새 글의 차별점을 먼저 정리하세요.")

    if risk_warnings:
        notes.append("스팸 회피 관점: 키워드 반복, 과장 표현, 중복 문장은 줄이는 편이 좋습니다.")
    else:
        notes.append("스팸 회피 관점: 현재 큰 위험 신호는 적지만 발행 전 반복 표현은 한 번 더 확인하세요.")

    return dedupe_keep_order(notes)[:4]


def build_photo_checklist(
    keyword: str,
    intent: str,
    body: str,
    content_stats: dict[str, int],
    missing_topics: list[str],
) -> list[str]:
    estimated_photo_count = content_stats.get("estimated_photo_count", 0)
    checklist: list[str] = []

    if intent in {"지역형", "후기형"}:
        checklist.extend(
            [
                "외관 또는 입구 사진 1장: 처음 가는 사람이 바로 찾을 수 있게 남기기",
                "대표 메뉴 또는 핵심 대상 사진 1장: 이 글의 결론이 보이는 장면 고르기",
                "메뉴판/가격표 사진 1장: 가격, 옵션, 주문 기준이 보이게 정리하기",
                "좌석/분위기 또는 현장 동선 사진 1장: 실제 공간 느낌을 설명과 함께 붙이기",
            ]
        )
        if "주차" in missing_topics or contains_any(body, ("주차", "공영주차장", "발렛")):
            checklist.append("주차 위치 또는 주변 접근 사진 1장: 초행 독자가 헤매지 않게 보강하기")
        if "웨이팅" in missing_topics or contains_any(body, ("웨이팅", "대기", "줄")):
            checklist.append("대기 동선 또는 혼잡 시간대 사진 1장: 붐비는 시간 설명과 함께 넣기")
    elif intent == "목록형":
        checklist.extend(
            [
                "후보별 대표 사진 1장씩: 제목에서 언급한 품목을 바로 구분할 수 있게 배치하기",
                "착용/사용 장면 사진 1장: 크기감과 분위기 차이가 보이게 남기기",
                "소재/디테일 근접 사진 1장: 질감, 마감, 포인트를 텍스트와 함께 설명하기",
                "가격 또는 구매처 캡처 1장: 비교 기준이 흔들리지 않게 출처를 붙이기",
            ]
        )
    elif intent == "비교형":
        checklist.extend(
            [
                "비교 대상이 한 화면에 같이 보이는 사진 1장",
                "차이점이 드러나는 근접 사진 1장",
                "가격/구성 차이를 보여주는 캡처 1장",
            ]
        )
    else:
        checklist.extend(
            [
                "핵심 절차나 결론을 보여주는 화면 캡처 1장",
                "중간 단계 또는 주의 포인트 캡처 1장",
                "최종 결과 또는 확인 화면 캡처 1장",
            ]
        )

    if estimated_photo_count == 0:
        checklist.insert(0, f"현재 본문에는 사진 흔적이 거의 없습니다. `{keyword}` 글이라면 핵심 장면 3장 이상을 먼저 확보해 두는 편이 안전합니다.")
    elif estimated_photo_count < 3:
        checklist.insert(0, f"사진이 약 {estimated_photo_count}개로 추정됩니다. 글 흐름을 받쳐줄 핵심 장면을 1~2개 더 보강하는 편이 좋습니다.")
    else:
        checklist.insert(0, f"사진이 약 {estimated_photo_count}개로 추정됩니다. 각 사진 앞뒤에 무엇을 확인해야 하는지 설명 문장을 붙이세요.")

    return dedupe_keep_order(checklist)[:6]


def build_differentiation_guidance(
    keyword: str,
    intent: str,
    missing_topics: list[str],
    serp_missing_topic_candidates: list[SerpMissingTopicCandidate],
    internal_link_candidates: list[InternalLinkCandidate],
    existing_post_overlap_warnings: list[ExistingPostOverlapWarning],
) -> list[str]:
    guidance: list[str] = []

    overlap_types = {warning.overlap_type for warning in existing_post_overlap_warnings}
    if "target_keyword" in overlap_types:
        guidance.append(f"이미 `{keyword}` 목표 키워드 글이 있으면 새 글은 같은 요약을 반복하지 말고 다른 상황, 최신 정보, 비교 기준 중 하나를 전면에 두세요.")
    elif "similar_keyword" in overlap_types:
        guidance.append("유사 키워드 글이 있으면 제목과 첫 문단에서 이번 글이 다루는 대상, 장소, 기준을 더 빨리 구분해 주세요.")
    elif "topic_overlap" in overlap_types:
        guidance.append("기존 글과 겹치는 정보는 내부 링크로 넘기고, 이번 글에서만 줄 수 있는 현장 판단이나 최신 업데이트를 앞쪽에 두세요.")

    matched_serp_topics = [candidate.topic for candidate in serp_missing_topic_candidates if candidate.matched_missing_topic]
    if matched_serp_topics:
        guidance.append(f"상위글에서 반복되는 {', '.join(matched_serp_topics[:3])} 정보는 기본값에 가깝습니다. 이 항목만 채우지 말고 본인 경험 기준의 판단을 같이 적으세요.")

    if missing_topics:
        guidance.append(f"차별화는 새로운 말을 억지로 만드는 것보다 기본 정보를 먼저 채운 뒤, 특히 `{missing_topics[0]}`처럼 빠진 항목에 실제 경험을 얹는 방식이 안전합니다.")

    if internal_link_candidates:
        first = internal_link_candidates[0]
        guidance.append(f"기존 글 `{first.title}`와 자연스럽게 연결하고, 이번 글은 그 글에 없는 정보만 더해 역할을 분리하세요.")

    intent_guides = {
        "지역형": "지역형 글은 같은 장소라도 방문 시간대, 좌석 선택, 주차/웨이팅 경험처럼 현장 조건을 구체화하면 차별화가 쉽습니다.",
        "후기형": "후기형 글은 좋았던 점만 쓰기보다 왜 그렇게 판단했는지와 아쉬운 점까지 같이 적어야 차별화됩니다.",
        "비교형": "비교형 글은 무엇이 더 좋다보다 어떤 사람에게 맞는지 기준을 분리해 쓰는 편이 설득력이 높습니다.",
        "목록형": "목록형 글은 후보 나열보다 고른 이유, 제외한 이유, 착용/사용 상황을 붙이면 복붙 느낌이 줄어듭니다.",
        "정보형": "정보형 글은 절차 설명만 반복하지 말고 실패 포인트, 준비물, 실제 소요 시간을 넣는 편이 더 유용합니다.",
    }
    guidance.append(intent_guides[intent])

    return dedupe_keep_order(guidance)[:5]


def duplicated_sentences(body: str) -> list[str]:
    sentences = [sentence for sentence in split_sentences(body) if len(sentence) >= 12]
    counts = Counter(sentences)
    return [sentence for sentence, count in counts.items() if count > 1]


def is_heading_like(line: str) -> bool:
    if len(line) > 42:
        return False
    if line.startswith(("#", "##")):
        return True
    if line.endswith(":"):
        return True
    return not line.endswith((".", "!", "?", "요", "다")) and len(line.split()) <= 6


def make_check(name: str, score: int, suggestions: list[str]) -> ContentCheck:
    max_score = CHECK_MAX_SCORES[name]
    return ContentCheck(
        name=name,
        score=max(0, min(score, max_score)),
        max_score=max_score,
        suggestions=dedupe_keep_order(suggestions),
    )


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    results = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        results.append(item)
    return results
