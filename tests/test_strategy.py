"""Financial failure boundaries and honest handling of unknown inputs."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugin/skills/emberbanter-growth-economics/scripts/studio_strategy.py"
spec = importlib.util.spec_from_file_location("studio_strategy", SCRIPT)
strategy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strategy)


class StrategyTests(unittest.TestCase):
    def scenario(self):
        return json.loads((ROOT / "plugin/assets/examples/economics.example.json").read_text())

    def test_synthetic_totals_and_conditional_target(self):
        result = strategy.economics(self.scenario())
        self.assertEqual(result["modeled_net_receipts"], "90.00")
        self.assertEqual(result["operating_result_before_tax"], "65.00")
        self.assertEqual(result["target_total_members"], 165)
        self.assertEqual(result["additional_members_for_target"], 145)
        self.assertTrue(result["not_a_forecast"])

    def test_missing_and_null_are_unknown_not_zero(self):
        data = self.scenario()
        del data["tips_net"]
        data["members"] = None
        result = strategy.economics(data)
        self.assertEqual(result["status"], "incomplete")
        self.assertIsNone(result["modeled_net_receipts"])
        self.assertEqual(set(result["missing"]), {"tips_net", "members"})

    def test_reject_invalid_rates_counts_and_double_count_alias(self):
        for change in ({"net_per_member": "NaN"}, {"tips_net": True},
                       {"ad_only_net_rpm": -1}, {"members": "1.5"},
                       {"rpm": 4}, {"ad_basis": "advertiser_cpm"}):
            with self.subTest(change=change), self.assertRaises(strategy.StrategyError):
                strategy.economics({**self.scenario(), **change})

    def test_missing_optional_target_preserves_known_profit(self):
        for null_value in (False, True):
            data = self.scenario()
            del data["target_profit"]
            if null_value:
                data["target_profit"] = None
            result = strategy.economics(data)
            self.assertEqual(result["modeled_net_receipts"], "90.00")
            self.assertEqual(result["operating_result_before_tax"], "65.00")
            self.assertIsNone(result["target_profit"])
            self.assertIsNone(result["target_total_members"])
            self.assertIsNone(result["additional_members_for_target"])

    def test_member_ceiling_uses_unrounded_decimal_and_zero_unit_income(self):
        data = self.scenario()
        for key in strategy.MONEY_FIELDS + strategy.COUNT_FIELDS:
            data[key] = 0
        data.update(net_per_member="0.07", target_profit="0.15")
        self.assertEqual(strategy.economics(data)["target_total_members"], 3)
        data.update(net_per_member="0.333", target_profit="1.00")
        self.assertEqual(strategy.economics(data)["target_total_members"], 4)
        data.update(net_per_member=0)
        result = strategy.economics(data)
        self.assertIsNone(result["target_total_members"])
        self.assertEqual(result["break_even_total_members"], 0)
        data.update(fixed_cost=1)
        self.assertIsNone(strategy.economics(data)["break_even_total_members"])

    def test_subjective_score_bounds_and_invalid_ratings(self):
        for rating, expected in ((0, "0.0"), (5, "100.0")):
            result = strategy.clip_score({key: rating for key in strategy.WEIGHTS})
            self.assertEqual(result["subjective_editorial_score"], expected)
            self.assertFalse(result["is_probability"])
            self.assertFalse(result["is_platform_algorithm"])
        for bad in (True, 6, -1, "Infinity"):
            with self.subTest(bad=bad), self.assertRaises(strategy.StrategyError):
                strategy.clip_score({key: bad for key in strategy.WEIGHTS})

    def test_windows_bom_and_incomplete_cli_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scenario.json"
            path.write_text(json.dumps(self.scenario()), encoding="utf-8-sig")
            completed = subprocess.run([sys.executable, str(SCRIPT), "economics", str(path)],
                                       capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["target_total_members"], 165)
            path.write_text("{}", encoding="utf-8-sig")
            completed = subprocess.run([sys.executable, str(SCRIPT), "economics", str(path)],
                                       capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            self.assertIsNone(json.loads(completed.stdout)["modeled_net_receipts"])


if __name__ == "__main__":
    unittest.main()
