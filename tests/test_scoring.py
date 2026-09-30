import unittest

from agent_eval.scoring import score_case, summary


DOCS = {"policy": "The refund window is 30 days."}
CASE = {"id": "refund", "context_ids": ["policy"],
        "expected": {"behavior": "answer", "must_contain": ["30 days"], "support_ids": ["policy"],
                     "must_not_contain": ["365 days"]}}


class ScoringTests(unittest.TestCase):
    def test_grounded_answer_passes(self):
        result = score_case(CASE, {"answer": "30 days.", "citations": ["policy"]}, DOCS)
        self.assertTrue(result["passed"])

    def test_wrong_number_fails_even_with_valid_citation(self):
        result = score_case(CASE, {"answer": "365 days, though also 30 days.", "citations": ["policy"]}, DOCS)
        self.assertFalse(result["passed"])
        self.assertTrue(result["hallucination_flag"])

    def test_uncited_answer_fails_grounding(self):
        result = score_case(CASE, {"answer": "30 days.", "citations": []}, DOCS)
        self.assertFalse(result["grounding_ok"])

    def test_foreign_citation_fails(self):
        result = score_case(CASE, {"answer": "30 days.", "citations": ["other"]}, DOCS)
        self.assertTrue(result["hallucination_flag"])

    def test_abstention_requires_no_citation(self):
        case = {"id": "unknown", "context_ids": ["policy"],
                "expected": {"behavior": "abstain", "must_contain": []}}
        self.assertTrue(score_case(case, {"answer": "I don't know based on the provided documents.", "citations": []}, DOCS)["passed"])
        self.assertFalse(score_case(case, {"answer": "Probably tomorrow.", "citations": ["policy"]}, DOCS)["passed"])

    def test_summary_rates(self):
        good = score_case(CASE, {"answer": "30 days.", "citations": ["policy"]}, DOCS)
        bad = score_case(CASE, {"answer": "365 days.", "citations": ["policy"]}, DOCS)
        result = summary([good, bad])
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["hallucination_flag_rate"], .5)


if __name__ == "__main__":
    unittest.main()
