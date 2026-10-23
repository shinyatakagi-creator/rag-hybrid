import threading

import pytest

from api.ledger import BudgetExhausted, Ledger


def test_reserve_settle_release_and_total(tmp_path):
    l = Ledger(tmp_path / "l.json", limit_usd=1.0)
    r1 = l.reserve(0.30, "a")
    assert l.status()["reserved_usd"] == 0.30 and l.status()["remaining_usd"] == pytest.approx(0.70)
    l.settle(r1, 0.12)  # real cost is lower than the worst case
    assert l.status() == {"limit_usd": 1.0, "settled_usd": 0.12, "reserved_usd": 0.0, "open_reservations": 0, "remaining_usd": pytest.approx(0.88)}
    r2 = l.reserve(0.5, "b")
    l.release(r2)  # call never reached the provider
    assert l.status()["settled_usd"] == 0.12 and l.status()["open_reservations"] == 0


def test_over_budget_reservation_is_refused_and_changes_nothing(tmp_path):
    l = Ledger(tmp_path / "l.json", limit_usd=0.10)
    l.reserve(0.06, "first")
    with pytest.raises(BudgetExhausted):
        l.reserve(0.05, "second")  # 0.06 reserved + 0.05 > 0.10
    assert l.status()["reserved_usd"] == 0.06 and l.status()["open_reservations"] == 1
    l.reserve(0.04, "fits exactly")


def test_a_reservation_blocks_others_until_settled(tmp_path):
    l = Ledger(tmp_path / "l.json", limit_usd=0.10)
    r = l.reserve(0.09)
    with pytest.raises(BudgetExhausted):
        l.reserve(0.02)
    l.settle(r, 0.01)
    l.reserve(0.05)  # the worst-case hold is gone, only the real cost counts


def test_state_survives_reopen_and_stale_reservations_count_as_spent_on_recovery(tmp_path):
    p = tmp_path / "l.json"
    l = Ledger(p, limit_usd=1.0)
    l.settle(l.reserve(0.2), 0.2)
    l.reserve(0.3, "left open by a crash")
    l2 = Ledger(p, limit_usd=1.0)
    assert l2.status()["settled_usd"] == 0.2 and l2.status()["open_reservations"] == 1
    assert l2.recover_stale() == 1 and l2.status()["settled_usd"] == pytest.approx(0.5) and l2.status()["open_reservations"] == 0


def test_seed_counts_outside_spend_against_the_same_limit(tmp_path):
    l = Ledger(tmp_path / "l.json", limit_usd=1.0)
    l.seed(0.95)
    with pytest.raises(BudgetExhausted):
        l.reserve(0.10)


def test_concurrent_reservations_never_exceed_the_limit(tmp_path):
    l = Ledger(tmp_path / "l.json", limit_usd=1.0)
    ok, bad = [], []

    def work():
        try:
            ok.append(l.reserve(0.1))
        except BudgetExhausted:
            bad.append(1)

    ts = [threading.Thread(target=work) for _ in range(25)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(ok) == 10 and len(bad) == 15 and l.status()["reserved_usd"] == pytest.approx(1.0)
