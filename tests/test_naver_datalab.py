import unittest

from core.naver_datalab import parse_datalab_home


class NaverDatalabTests(unittest.TestCase):
    def test_parse_datalab_home_returns_latest_keyword_rank_card(self):
        source = """
        <div class="keyword_rank">
          <div class="rank_inner v2">
            <strong class="rank_title"><span class="title_cell">2026.04.17.(금)</span></strong>
            <div class="rank_scroll"><ul class="rank_list">
              <li class="list"><a href="/shoppingInsight/sKeyword.naver?keyword=%EC%9B%90%ED%94%BC%EC%8A%A4" class="list_area"><em class="num">1</em><span class="title">원피스</span></a></li>
            </ul></div>
          </div>
        </div>
        <div class="keyword_rank">
          <div class="rank_inner v2">
            <strong class="rank_title"><span class="title_cell">2026.04.18.(토)</span></strong>
            <div class="rank_scroll"><ul class="rank_list">
              <li class="list"><a href="/shoppingInsight/sKeyword.naver?keyword=%EB%B8%94%EB%9D%BC%EC%9A%B0%EC%8A%A4" class="list_area"><em class="num">1</em><span class="title">블라우스</span></a></li>
              <li class="list"><a href="/shoppingInsight/sKeyword.naver?keyword=%EB%B0%94%EB%9E%8C%EB%A7%89%EC%9D%B4" class="list_area"><em class="num">2</em><span class="title">바람막이</span></a></li>
            </ul></div>
          </div>
        </div>
        """

        result = parse_datalab_home(source, category="50000000")

        self.assertEqual(result.source, "naver_datalab_shopping_insight")
        self.assertEqual(result.category["name"], "패션의류")
        self.assertEqual(result.period, "2026.04.18.(토)")
        self.assertEqual(result.items[0].rank, 1)
        self.assertEqual(result.items[0].keyword, "블라우스")
        self.assertTrue(result.items[0].url.startswith("https://datalab.naver.com/"))


if __name__ == "__main__":
    unittest.main()
