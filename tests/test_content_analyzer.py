import unittest

from core.content_analyzer import (
    CHECK_COVERAGE,
    CHECK_RISKS,
    CHECK_SEARCH_INTENT,
    ContentAnalysisRequest,
    OwnerPostContext,
    ReferencePost,
    analyze_content,
    content_analysis_to_dict,
)


class ContentAnalyzerTests(unittest.TestCase):
    def test_analyze_content_returns_internal_proxy_score_and_checks(self):
        body = """
        방문 목적과 결론
        2026년 4월에 서촌 카페 스태픽스에 직접 방문했습니다.
        결론부터 말하면 조용한 분위기와 넓은 좌석이 좋아서 데이트 코스로 추천할 만했습니다.

        위치와 주차
        경복궁역에서 걸어갔고 주소, 영업시간, 예약 가능 여부를 확인했습니다.
        주차는 근처 공영주차장을 쓰는 편이 좋고, 주말에는 웨이팅이 있었습니다.

        메뉴와 가격
        대표 메뉴 가격과 맛을 적고 사진 설명도 함께 넣었습니다.
        장점은 분위기와 커피 맛이고, 단점은 사람이 몰리는 시간대입니다.
        """

        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="서촌 카페 스태픽스 직접 방문 후기",
                body=body,
            )
        )

        self.assertGreaterEqual(result.score, 70)
        self.assertIn("내부 프록시 점수", result.score_label)
        self.assertEqual(sum(check.max_score for check in result.checks), 100)
        self.assertEqual(
            [check.name for check in result.checks],
            [
                "검색 의도 일치도",
                "제목/첫문단 명확성",
                "구조와 가독성",
                "키워드/관련어 커버리지",
                "경험/신뢰 요소",
                "독자 기대 정보 누락",
                "위험 요소",
            ],
        )
        self.assertTrue(result.priority_actions)
        self.assertTrue(result.title_suggestions)
        self.assertTrue(result.heading_suggestions)
        self.assertTrue(result.benchmark_notes)
        self.assertTrue(result.photo_checklist)
        self.assertTrue(result.differentiation_guidance)

    def test_analyze_content_flags_keyword_stuffing_and_hype(self):
        body = "서촌 카페 최고. 서촌 카페 최고. 서촌 카페 최고. 무조건 100% 완벽 추천."

        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="서촌 카페 서촌 카페 서촌 카페",
                body=body,
            )
        )

        risk_check = next(check for check in result.checks if check.name == CHECK_RISKS)
        self.assertLess(risk_check.score, risk_check.max_score)
        self.assertTrue(any("키워드 반복" in warning for warning in result.risk_warnings))
        self.assertTrue(any("과장" in warning for warning in result.risk_warnings))

    def test_related_coverage_and_intent_suggestions_are_returned_for_thin_body(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="주말에 간 예쁜 곳",
                body="분위기가 좋았습니다.",
            )
        )

        checks = {check.name: check for check in result.checks}
        self.assertTrue(checks[CHECK_SEARCH_INTENT].suggestions)
        self.assertTrue(checks[CHECK_COVERAGE].suggestions)
        self.assertIn("위치", result.missing_topics)

    def test_empty_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            analyze_content(ContentAnalysisRequest(keyword="", title="제목", body="본문"))

    def test_content_analysis_to_dict_serializes_nested_checks(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="서촌 카페 방문 후기",
                body="서촌 카페에 직접 방문했습니다. 가격과 위치를 확인했습니다.",
            )
        )

        payload = content_analysis_to_dict(result)

        self.assertIsInstance(payload["checks"], list)
        self.assertIn("score", payload)
        self.assertIn("score_label", payload)
        self.assertIn("benchmark_notes", payload)
        self.assertIn("input_warnings", payload)
        self.assertIn("content_stats", payload)
        self.assertIn("photo_checklist", payload)
        self.assertIn("differentiation_guidance", payload)

    def test_pasted_image_gaps_are_collapsed_before_analysis(self):
        body = "첫 문단입니다.\n\n\n\n\n사진 다음 설명입니다.\n\n\n위치와 가격을 적었습니다."

        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="서촌 카페 방문 후기",
                body=body,
            )
        )

        self.assertTrue(any("빈 줄" in warning for warning in result.input_warnings))
        self.assertEqual(result.content_stats["estimated_photo_count"], 2)
        self.assertTrue(result.benchmark_notes)

    def test_naver_map_paste_boilerplate_is_normalized(self):
        body = """
        위치안동휴게소(춘천방향)
        50m

        © NAVER Corp.
        안동휴게소(춘천방향)
        경상북도 안동시 풍산읍 풍산태사로 1913-40

        화덕구이 간고등어를 먹었습니다.
        """

        result = analyze_content(
            ContentAnalysisRequest(
                keyword="안동휴게소 맛집",
                title="안동휴게소 간고등어 식사 후기",
                body=body,
            )
        )

        self.assertEqual(result.content_stats["map_place_count"], 1)
        self.assertTrue(any("지도" in warning for warning in result.input_warnings))
        payload = content_analysis_to_dict(result)
        self.assertEqual(payload["content_stats"]["map_place_count"], 1)

    def test_serp_title_summary_candidates_connect_to_missing_topics(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="서촌 카페 조용한 곳",
                body="서촌 카페에 다녀왔습니다. 창가 자리가 조용했습니다.",
                reference_posts=[
                    ReferencePost(
                        title="서촌 카페 주차 가능한 곳",
                        summary="위치와 주차, 대표 메뉴를 정리했습니다.",
                        url="https://blog.naver.com/a/1",
                    ),
                    ReferencePost(
                        title="서촌 카페 메뉴와 주차 후기",
                        summary="영업시간, 웨이팅, 가격 정보를 확인했습니다.",
                        url="https://blog.naver.com/b/2",
                    ),
                    ReferencePost(
                        title="서촌 카페 예약 전 확인할 것",
                        summary="주차와 예약 가능 여부를 함께 봤습니다.",
                        url="https://blog.naver.com/c/3",
                    ),
                ],
            )
        )

        topics = {candidate.topic: candidate for candidate in result.serp_missing_topic_candidates}
        self.assertIn("주차", topics)
        self.assertTrue(topics["주차"].matched_missing_topic)
        self.assertIn("독자 기대 정보 확인용", topics["주차"].guidance)
        self.assertNotIn("위치", topics)
        payload = content_analysis_to_dict(result)
        self.assertIn("serp_missing_topic_candidates", payload)
        self.assertTrue(payload["serp_missing_topic_candidates"][0]["matched_missing_topic"])

    def test_owner_posts_add_internal_links_and_overlap_warnings(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="서촌 카페 조용한 신상 카페 후기",
                body=(
                    "서촌 카페에 다녀왔습니다. 조용한 좌석과 커피 맛을 중심으로 적었습니다.\n"
                    "주차는 근처 공영주차장을 이용했고 메뉴 가격도 확인했습니다."
                ),
                owner_posts=[
                    OwnerPostContext(
                        post_id=1,
                        title="서촌 카페 주차 후기",
                        url="https://blog.naver.com/myblog/1",
                        category="카페",
                        published_at="2026. 04. 10.",
                        content_summary="서촌 카페 주차와 메뉴 가격을 정리한 글",
                        content_text="서촌 공영주차장, 메뉴판, 가격, 웨이팅 정보를 담았습니다.",
                        keywords=["서촌 카페"],
                    ),
                    OwnerPostContext(
                        post_id=2,
                        title="성수 전시 후기",
                        url="https://blog.naver.com/myblog/2",
                        content_summary="전시 관람 후기",
                        content_text="전시 예약과 관람 동선",
                        keywords=["성수 전시"],
                    ),
                ],
            )
        )

        self.assertEqual(result.internal_link_candidates[0].post_id, 1)
        self.assertTrue(result.internal_link_candidates[0].reasons)
        self.assertEqual(result.existing_post_overlap_warnings[0].overlap_type, "target_keyword")
        self.assertEqual(result.existing_post_overlap_warnings[0].matched_posts[0].post_id, 1)
        payload = content_analysis_to_dict(result)
        self.assertIn("internal_link_candidates", payload)
        self.assertIn("existing_post_overlap_warnings", payload)

    def test_wishlist_keyword_uses_list_intent_and_filters_noisy_overlap(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword=(
                    "#봄가방추천 #숄더백추천 #백팩추천 #가방추천 #데일리백추천 "
                    "[위시리스트] 봄 가방 추천 :: 숄더백·백팩 모음ㅣ미닛뮤트ㅣ분크"
                ),
                title="[위시리스트] 봄 가방 추천 :: 숄더백·백팩 모음",
                body=(
                    "봄 가방 위시리스트를 브랜드별로 정리했습니다.\n"
                    "미닛뮤트는 가죽 소재와 수납이 좋고, 분크는 출근 코디에 맞습니다.\n"
                    "가격, 크기, 착용 느낌, 구매처를 후보별로 비교해 적었습니다."
                ),
                reference_posts=[
                    ReferencePost(title="여자 backpack 추천", summary="backpack 데일리 backpack"),
                    ReferencePost(title="봄 가방 미니백 위시리스트", summary="브랜드 가격 소재"),
                    ReferencePost(title="데일리 미니백 모음", summary="브랜드별 크기와 수납"),
                ],
                owner_posts=[
                    OwnerPostContext(
                        post_id=1,
                        title="미닛뮤트 리무드백 리뷰",
                        url="https://blog.naver.com/myblog/1",
                        content_summary="미닛뮤트 가죽 가방 가격과 수납",
                        content_text="ㅋㅋ ㅠㅠ 000원 같다 같은 가운데 가격도 가능하다",
                        keywords=["미닛뮤트 가방"],
                    ),
                    OwnerPostContext(
                        post_id=2,
                        title="전혀 다른 여행 글",
                        url="https://blog.naver.com/myblog/2",
                        content_summary="오사카 여행 일정",
                        content_text="ㅋㅋ ㅠㅠ 000원 같다 같은 가운데 가격도 가능하다",
                        keywords=["오사카 여행"],
                    ),
                ],
            )
        )

        self.assertEqual(result.intent, "목록형")
        self.assertFalse(any(topic in result.missing_topics for topic in ("비교", "차이", "순위")))
        self.assertTrue(all("backpack" != candidate.topic for candidate in result.serp_missing_topic_candidates))
        self.assertTrue(result.title_suggestions[0].startswith("봄 가방 추천"))
        self.assertLessEqual(len(result.existing_post_overlap_warnings), 1)

    def test_published_clothing_wishlist_suppresses_generic_feedback(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword="여쿨라셔츠 여쿨라블라우스 도매택셔츠",
                title=(
                    "여쿨라셔츠 여쿨라블라우스 도매택셔츠 "
                    "[위시리스트] 여쿨라 도매택 셔츠·블라우스 추천"
                ),
                body=(
                    "오늘은 도매택 셔츠들이랑 소장하고 있는 블라우스까지 가져왔다.\n"
                    "프리티영띵 리옹 체크 셔츠 37,500 s.zigzag.kr\n"
                    "맑은 하늘색 바탕에 체크 패턴이 들어가 있고 흰 원피스 위에 걸쳐 입어도 좋다.\n"
                    "미엘 체크 셔츠는 라벤더 톤을 베이스로 코디하기 좋고 여름 뮤트 톤에 맞다.\n"
                    "리터 셔츠는 링클 소재이고 기장감도 길어서 힙라인 커버가 가능하다.\n"
                    "얀13 블라우스는 하객룩과 출근룩으로 입기 좋고 착샷과 함께 정리했다.\n"
                    "#여쿨라셔츠 #여쿨라블라우스 #도매택셔츠"
                ),
                reference_posts=[
                    ReferencePost(title="도매택 셔츠 후보", summary="같음 착용 레이어드"),
                    ReferencePost(title="여쿨라 블라우스 착용", summary="같음 가디건 레이어드"),
                    ReferencePost(title="도매택 셔츠 코디", summary="후보 착용"),
                ],
                owner_posts=[
                    OwnerPostContext(
                        post_id=1,
                        title="여쿨라 봄옷 위시리스트",
                        url="https://blog.naver.com/myblog/1",
                        content_summary="도매택 셔츠와 미엘 블라우스 코디",
                        content_text="가지 갠적으로 겁나 게시글의 같고 셔츠 블라우스 미엘 코디",
                        keywords=["여쿨라 봄옷"],
                    )
                ],
            )
        )

        self.assertEqual(result.intent, "목록형")
        self.assertFalse(any(topic in result.missing_topics for topic in ("후보", "가격", "크기", "수납", "착용")))
        self.assertTrue(all(candidate.topic not in {"후보", "같음"} for candidate in result.serp_missing_topic_candidates))
        if result.internal_link_candidates:
            reasons = " ".join(result.internal_link_candidates[0].reasons)
            self.assertNotIn("갠적으로", reasons)
            self.assertNotIn("게시글의", reasons)

    def test_photo_checklist_and_differentiation_guidance_are_contextual(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword="서촌 카페",
                title="서촌 카페 조용한 좌석 후기",
                body="서촌 카페에 다녀왔습니다. 조용한 좌석과 커피 맛을 적었습니다.",
                reference_posts=[
                    ReferencePost(title="서촌 카페 주차 후기", summary="주차와 메뉴, 웨이팅 정리"),
                    ReferencePost(title="서촌 카페 메뉴와 가격", summary="주차, 가격, 대표 메뉴"),
                ],
                owner_posts=[
                    OwnerPostContext(
                        post_id=1,
                        title="서촌 카페 주차 후기",
                        url="https://blog.naver.com/myblog/1",
                        content_summary="주차와 메뉴 정리",
                        content_text="주차, 메뉴판, 가격, 웨이팅",
                        keywords=["서촌 카페"],
                    )
                ],
            )
        )

        self.assertTrue(any("메뉴판" in item or "가격표" in item for item in result.photo_checklist))
        self.assertTrue(any("기존 글" in item or "이미" in item for item in result.differentiation_guidance))

    def test_editor_media_markers_are_counted_as_photo_slots(self):
        body = """
        충남 아산 피나클랜드

        AI 활용 설정
        사진 설명을 입력하세요.

        메인 주차장

        출처 입력
        AI 활용 설정
        사진 설명을 입력하세요.

        운영시간과 요금을 적었습니다.
        """

        result = analyze_content(
            ContentAnalysisRequest(
                keyword="피나클랜드 튤립",
                title="충남 아산 피나클랜드 튤립 후기",
                body=body,
            )
        )

        self.assertGreaterEqual(result.content_stats["estimated_photo_count"], 2)
        self.assertTrue(any("사진 자리" in warning for warning in result.input_warnings))

    def test_review_feedback_handles_hashtag_keyword_and_paid_visit_signals(self):
        result = analyze_content(
            ContentAnalysisRequest(
                keyword="#피나클랜드 #아산피나클랜드 #피나클랜드튤립",
                title="충남 아산 피나클랜드 애견 동반 가능한 튤립명소",
                body=(
                    "평일 기준 사람도 비교적 적고 튤립도 거의 절정 분위기라 사진 찍기 좋았습니다.\n"
                    "우리는 네이버 예약 후 현장에서 티켓을 발권했고 대인 15,000원, 네이버 예약 시 1,000원 할인도 확인했습니다.\n"
                    "무엇보다 평일에는 애견동반이 가능해서 만족스러웠습니다. 다만 튤립 시즌에는 메인 주차장이 만차일 수 있어 여유 있게 도착하는 편이 좋습니다."
                ),
            )
        )

        self.assertNotIn("내돈내산", result.missing_topics)
        self.assertNotIn("경험", result.missing_topics)
        self.assertNotIn("맛", result.missing_topics)
        self.assertTrue(all("아산피나클랜드 피나클랜드튤립" not in item for item in result.title_suggestions))
        self.assertFalse(any(item == "내돈내산 확인" for item in result.heading_suggestions))

    def test_realistic_review_draft_is_not_stuck_in_low_70s(self):
        body = """
        충남 아산 피나클랜드 애견 동반 가능한 튤립명소
        평일 기준 사람도 비교적 적고, 튤립도 거의 절정 분위기라 사진 찍기 좋았습니다.
        무엇보다 평일에는 애견동반이 가능해서 강아지와 함께 봄나들이 하기에도 만족스러웠습니다.

        피나클랜드 한눈에 보기
        평일 기준 애견 동반 가능
        튤립 개화상태는 80% 이상
        평일 혼잡도가 낮아 주말보다 방문 만족도가 높음

        위치 및 주차
        충청남도 아산시 영인면 월선길 20-22
        무료 주차 가능
        다만 튤립 시즌에는 만차일 가능성이 높아 보여 여유 있게 도착하는 걸 추천합니다.

        요금 및 애견동반
        대인 15,000원
        네이버 예약 시 1,000원 할인
        우리는 네이버 예약 후 현장에서 티켓을 발권했습니다.
        평일 입장 가능, 주말 공휴일 입장 불가능, 15kg 이하 가능

        AI 활용 설정
        사진 설명을 입력하세요.
        출처 입력
        AI 활용 설정
        사진 설명을 입력하세요.
        """

        result = analyze_content(
            ContentAnalysisRequest(
                keyword="피나클랜드 튤립 애견동반",
                title="충남 아산 피나클랜드 애견 동반 가능한 튤립명소",
                body=body,
            )
        )

        self.assertGreaterEqual(result.score, 80)


if __name__ == "__main__":
    unittest.main()
