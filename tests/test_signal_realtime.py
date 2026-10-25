import unittest

from core.signal_realtime import parse_signal_realtime


class SignalRealtimeTests(unittest.TestCase):
    def test_parse_signal_realtime_returns_top10_keywords(self):
        result = parse_signal_realtime(
            {
                "now": 1776702791523,
                "top10": [
                    {"rank": 1, "keyword": "이재명, 한-인도 포럼 발언", "state": "s", "summary": "https://summary.signal.bz/1"},
                    {"rank": 2, "keyword": "일본 7.4 지진", "state": "+", "summary": "https://summary.signal.bz/2"},
                ],
            }
        )

        self.assertEqual(result.source, "signal_realtime")
        self.assertEqual(result.source_label, "Signal 실시간 검색어")
        self.assertEqual(result.items[0].rank, 1)
        self.assertEqual(result.items[0].keyword, "이재명, 한-인도 포럼 발언")
        self.assertEqual(result.items[1].state, "+")


if __name__ == "__main__":
    unittest.main()
