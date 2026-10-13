import json
import unittest
from pathlib import Path

from deal_structurer import normalize_profile, recommend, to_dict, to_markdown
from deal_structurer.__main__ import main
from deal_structurer.engine import FIELDS, load_json

EXAMPLES = Path(__file__).parent.parent / "examples"


def ids(evals):
    return [e.structure["id"] for e in evals]


class DataIntegrityTest(unittest.TestCase):
    def test_rules_reference_known_fields_and_values(self):
        for s in load_json("structures.json")["structures"]:
            for rule in s["rules"]:
                self.assertTrue("score" in rule or rule.get("exclude"), s["id"])
                for key, values in rule["if"].items():
                    self.assertIn(key, FIELDS, f"{s['id']}: {key}")
                    choices = FIELDS[key][1]
                    if choices is not None:
                        for v in values:
                            self.assertIn(v, choices, f"{s['id']}: {key}={v}")

    def test_cases_reference_known_structures(self):
        known = {s["id"] for s in load_json("structures.json")["structures"]}
        for c in load_json("cases.json")["cases"]:
            self.assertTrue(set(c["structures"]) <= known, c["id"])

    def test_core_structures_have_all_attributes(self):
        attrs = set(load_json("structures.json")["attributes"])
        for s in load_json("structures.json")["structures"]:
            if s["kind"] == "core":
                self.assertEqual(set(s["attrs"]), attrs, s["id"])


class ProfileTest(unittest.TestCase):
    def test_defaults_filled(self):
        self.assertEqual(normalize_profile({})["objective"], "control")

    def test_invalid_value_rejected(self):
        with self.assertRaises(ValueError):
            normalize_profile({"liability_risk": "extreme"})

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            normalize_profile({"foo": 1})


class RecommendTest(unittest.TestCase):
    def test_env_buyout_prefers_share_deal_and_excludes_swap_for_pe(self):
        rec = recommend(json.loads((EXAMPLES / "env_incinerator_buyout.json").read_text()))
        self.assertEqual(rec.core[0].structure["id"], "share_purchase")
        self.assertIn("share_swap", ids(rec.excluded))
        self.assertIn("tender_offer", ids(rec.excluded))
        self.assertIn("escrow_adjustment", ids(rec.overlays))
        self.assertTrue(all("환경" in c["industry"] for c in rec.core[0].cases))

    def test_capital_raise_prefers_new_shares(self):
        rec = recommend(json.loads((EXAMPLES / "growth_investment.json").read_text()))
        self.assertEqual(rec.core[0].structure["id"], "new_share_issue")
        self.assertIn("mezzanine_terms", ids(rec.overlays))
        self.assertNotIn("earn_out", ids(rec.overlays))

    def test_carve_out_prefers_split(self):
        rec = recommend(json.loads((EXAMPLES / "division_carve_out.json").read_text()))
        self.assertEqual(rec.core[0].structure["id"], "split_off_sale")
        self.assertNotIn("share_purchase", ids(rec.core))
        self.assertNotIn("lbo_financing", ids(rec.overlays))

    def test_listed_target_allows_tender_offer(self):
        rec = recommend({"target_listed": True, "urgency": "high", "buyer_cash": "high"})
        self.assertIn("tender_offer", ids(rec.core))

    def test_deal_size_threshold(self):
        small = recommend({"deal_size_eok": 1000, "buyer_cash": "low"})
        large = recommend({"deal_size_eok": 8000, "buyer_cash": "low"})
        score = lambda r: next(e.score for e in r.overlays if e.structure["id"] == "consortium")
        self.assertEqual(score(large), score(small) + 1)

    def test_outputs_render(self):
        rec = recommend({"industry": "환경"})
        md = to_markdown(rec)
        self.assertIn("## 4. 대안별 상세 분석", md)
        self.assertIn("에코비트", md)
        json.dumps(to_dict(rec), ensure_ascii=False)


class CliTest(unittest.TestCase):
    def test_bad_profile_returns_error_code(self):
        tmp = Path(__file__).parent / "_bad.json"
        tmp.write_text('{"stake": "all"}')
        try:
            self.assertEqual(main(["--profile", str(tmp)]), 2)
        finally:
            tmp.unlink()


if __name__ == "__main__":
    unittest.main()
