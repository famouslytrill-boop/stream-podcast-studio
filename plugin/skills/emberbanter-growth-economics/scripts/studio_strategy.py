#!/usr/bin/env python3
"""Explicit local scenario arithmetic and subjective clip scoring. No network or posting."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP, localcontext
import json
from pathlib import Path
import re
import sys

MONEY_FIELDS = ("net_per_member", "ad_only_net_rpm", "sponsor_net", "affiliate_net",
                "tips_net", "other_net", "fixed_cost", "variable_cost", "target_profit")
COUNT_FIELDS = ("members", "ad_basis_views")
META_FIELDS = ("label", "data_kind", "currency", "period", "ad_basis")
WEIGHTS = {"clarity": 25, "context": 20, "payoff": 25, "audio": 15, "legibility": 15}


class StrategyError(ValueError):
    pass


def number(value, key, *, integer=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise StrategyError(f"{key} must be an explicit finite nonnegative number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise StrategyError(f"{key} is not numeric") from exc
    if not result.is_finite() or result < 0 or result > Decimal("1000000000000"):
        raise StrategyError(f"{key} must be finite and between zero and one trillion")
    if integer and result != result.to_integral_value():
        raise StrategyError(f"{key} must be a whole count")
    return result


def money(value):
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def economics(data):
    if not isinstance(data, dict):
        raise StrategyError("Scenario must be a JSON object")
    allowed = set(MONEY_FIELDS + COUNT_FIELDS + META_FIELDS + ("_note",))
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise StrategyError("Unknown fields: " + ", ".join(unknown)
                            + "; aggregate RPM/CPM cannot replace ad_only_net_rpm")
    missing = [k for k in MONEY_FIELDS + COUNT_FIELDS + META_FIELDS
               if k != "target_profit" and data.get(k) is None]
    if missing:
        return {"status": "incomplete", "missing": missing, "modeled_net_receipts": None,
                "operating_result_before_tax": None, "not_a_forecast": True}
    for key in ("label", "period"):
        if not isinstance(data[key], str) or not data[key].strip() or len(data[key]) > 200:
            raise StrategyError(f"{key} needs a nonempty label of at most 200 characters")
    if data["data_kind"] not in ("hypothetical", "observed"):
        raise StrategyError("data_kind must be hypothetical or observed")
    if not isinstance(data["currency"], str) or not re.fullmatch(r"[A-Z]{3}", data["currency"]):
        raise StrategyError("currency must be one uppercase three-letter currency code")
    if data["ad_basis"] not in ("all_video_views", "shorts_engaged_views"):
        raise StrategyError("ad_basis must identify all_video_views or shorts_engaged_views")
    values = {k: number(data[k], k, integer=k in COUNT_FIELDS)
              for k in MONEY_FIELDS + COUNT_FIELDS if data.get(k) is not None}
    with localcontext() as ctx:
        ctx.prec = 50
        membership = values["members"] * values["net_per_member"]
        ads = values["ad_basis_views"] / 1000 * values["ad_only_net_rpm"]
        other = ads + sum(values[k] for k in ("sponsor_net", "affiliate_net", "tips_net", "other_net"))
        receipts = membership + other
        cost = values["fixed_cost"] + values["variable_cost"]

        def required_members(profit):
            gap = max(Decimal(0), cost + profit - other)
            if gap == 0:
                return 0
            if values["net_per_member"] == 0:
                return None
            return int((gap / values["net_per_member"]).to_integral_value(rounding=ROUND_CEILING))

        target = required_members(values["target_profit"]) if "target_profit" in values else None
        return {"status": "calculated", "label": data["label"], "data_kind": data["data_kind"],
                "currency": data["currency"], "period": data["period"], "ad_basis": data["ad_basis"],
                "membership_net": money(membership), "ad_net": money(ads),
                "nonmembership_net": money(other), "modeled_net_receipts": money(receipts),
                "modeled_cost": money(cost), "operating_result_before_tax": money(receipts - cost),
                "break_even_total_members": required_members(Decimal(0)),
                "target_profit": money(values["target_profit"]) if "target_profit" in values else None,
                "target_total_members": target,
                "additional_members_for_target": None if target is None else max(0, target-int(values["members"])),
                "not_a_forecast": True,
                "limits": ["Disjoint net receipts in one currency and period; no currency conversion.",
                           "Ad-only rate must use the same view basis; aggregate RPM or advertiser CPM is invalid.",
                           "Targets hold all other receipts, per-member net and costs constant.",
                           "Taxes, unpaid owner labor and equipment depreciation excluded unless explicitly costed.",
                           "Inputs are supplied assumptions or records, not verified eligibility or payout guarantees."]}


def clip_score(data):
    if not isinstance(data, dict) or set(data) != set(WEIGHTS):
        raise StrategyError("Score needs exactly clarity, context, payoff, audio and legibility")
    ratings = {k: number(data[k], k) for k in WEIGHTS}
    if any(v > 5 for v in ratings.values()):
        raise StrategyError("Every subjective rating must be between zero and five")
    score = sum(ratings[k] / 5 * weight for k, weight in WEIGHTS.items())
    return {"subjective_editorial_score": str(score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)),
            "scale": "0-100", "weights": WEIGHTS, "is_platform_algorithm": False,
            "is_probability": False, "review": "Context, rights, captions and sound still need review."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("economics", "clip-score"))
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        if not args.input.is_file() or args.input.stat().st_size > 100_000:
            raise StrategyError("Use a local JSON file of at most 100 KB")
        data = json.loads(args.input.read_text(encoding="utf-8-sig"), parse_float=Decimal)
        result = economics(data) if args.command == "economics" else clip_score(data)
        print(json.dumps(result, indent=2))
        return 2 if result.get("status") == "incomplete" else 0
    except (OSError, UnicodeError, ValueError, InvalidOperation) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
