from main import generate, reconcile


def test_correct_one_to_one_matches():
    bank, ledger, truth = generate()
    result = reconcile(bank, ledger)
    assert all(truth[r["bank"]] == r["ledger"] for r in result["matches"])
    assert len({r["ledger"] for r in result["matches"]}) == len(result["matches"])
    assert result["exceptions"]


def test_ambiguous_candidates_are_not_forced():
    row = {
        "id": "b",
        "cents": 100,
        "currency": "USD",
        "day": 1,
        "description": "Synthetic Merchant",
    }
    result = reconcile([row], [{**row, "id": "l1"}, {**row, "id": "l2"}])
    assert not result["matches"] and result["exceptions"][0]["reason"] == "ambiguous candidates"
