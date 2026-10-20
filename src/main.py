"""Explain conservative one-to-one matches on noisy synthetic financial records."""

import json
import random
import re
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def reconcile(bank: list[dict], ledger: list[dict]) -> dict:
    used = set()
    matches = []
    exceptions = []
    for transaction in bank:
        candidates = []
        for entry in ledger:
            if (
                entry["id"] in used
                or transaction["currency"] != entry["currency"]
                or transaction["cents"] != entry["cents"]
            ):
                continue
            days = abs(transaction["day"] - entry["day"])
            if days > 2:
                continue
            ratio = SequenceMatcher(
                None, normalize(transaction["description"]), normalize(entry["description"])
            ).ratio()
            if ratio >= 0.7:
                candidates.append((ratio - days * 0.03, entry["id"]))
        candidates.sort(reverse=True)
        if candidates and (len(candidates) == 1 or candidates[0][0] - candidates[1][0] >= 0.1):
            score, entry_id = candidates[0]
            used.add(entry_id)
            matches.append(
                {
                    "bank": transaction["id"],
                    "ledger": entry_id,
                    "score": score,
                    "reason": "same integer cents and currency; date window; normalized description similarity",
                }
            )
        else:
            exceptions.append(
                {
                    "bank": transaction["id"],
                    "reason": "ambiguous candidates" if candidates else "no compatible entry",
                }
            )
    return {"matches": matches, "exceptions": exceptions}


def generate() -> tuple[list[dict], list[dict], dict]:
    rng = random.Random(42)
    bank = []
    ledger = []
    truth = {}
    for i in range(200):
        row = {
            "id": f"B{i}",
            "cents": rng.randint(1000, 1000000),
            "currency": "USD",
            "day": rng.randint(1, 28),
            "description": f"Synthetic Merchant {i}",
        }
        bank.append(row)
        if i < 180:
            entry = {
                **row,
                "id": f"L{i}",
                "description": f"SYNTHETIC-MERCHANT-{i}",
                "day": row["day"] + (1 if i % 3 == 0 else 0),
            }
            if i % 13 == 0:
                entry["cents"] += 1
            ledger.append(entry)
            truth[row["id"]] = entry["id"]
    return bank, ledger, truth


def benchmark() -> dict:
    bank, ledger, truth = generate()
    result = reconcile(bank, ledger)
    correct = sum(truth.get(r["bank"]) == r["ledger"] for r in result["matches"])
    Path("evidence/reconciliation.json").write_text(json.dumps(result, indent=2))
    pd.DataFrame(bank).to_csv("evidence/synthetic-bank.csv", index=False)
    pd.DataFrame(ledger).to_csv("evidence/synthetic-ledger.csv", index=False)
    return {
        "bank_transactions": len(bank),
        "matches": len(result["matches"]),
        "match_rate": len(result["matches"]) / len(bank),
        "false_match_rate": (len(result["matches"]) - correct) / len(result["matches"])
        if result["matches"]
        else None,
        "exceptions": len(result["exceptions"]),
    }


if __name__ == "__main__":
    print(json.dumps(benchmark(), indent=2))
