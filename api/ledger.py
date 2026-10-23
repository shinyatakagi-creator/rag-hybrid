"""File-backed cumulative spend ledger for the API (survives restarts, shared by all requests and workers on this machine).

    reserve(usd)   adds the FULL worst-case charge to the total before a paid call; refuses (BudgetExhausted) if settled + reserved + usd
                   would pass the limit, in which case the caller makes no paid call
    settle(id, x)  replaces the reservation by the real cost after the call
    release(id)    drops a reservation whose call never reached the provider (nothing was billed)

State lives in one small JSON file (default data/api/spend_ledger.json, gitignored), updated under an exclusive file lock and
replaced atomically. Reservations left open by a crash are converted to spent at their reserved amount when the app starts
(conservative: a call might have been billed).

    python -m api.ledger status
    python -m api.ledger seed 1.03     # count spend made outside the API (e.g. the eval runs) against the same limit
"""
import argparse
import fcntl
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = "data/api/spend_ledger.json"


class BudgetExhausted(RuntimeError):
    """The requested reservation would pass MAX_SPEND_USD. No paid call is made."""


class Ledger:
    def __init__(self, path=DEFAULT_PATH, limit_usd: float = 5.0):
        self.path, self.limit = Path(path), float(limit_usd)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_suffix(".lock")
        self._tlock = threading.Lock()
        if not self.path.exists():
            self._write({"settled_usd": 0.0, "reserved": {}, "events": 0})

    # -- low level -------------------------------------------------------------------------------
    def _read(self) -> dict:
        return json.loads(self.path.read_text())

    def _write(self, state: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state))
        os.replace(tmp, self.path)

    class _Txn:
        def __init__(self, ledger):
            self.l = ledger

        def __enter__(self):
            self.l._tlock.acquire()
            self.fh = open(self.l._lock_path, "a")
            fcntl.flock(self.fh, fcntl.LOCK_EX)
            self.state = self.l._read()
            return self.state

        def __exit__(self, exc_type, exc, tb):
            try:
                if exc_type is None:
                    self.state["events"] = self.state.get("events", 0) + 1
                    self.l._write(self.state)
            finally:
                fcntl.flock(self.fh, fcntl.LOCK_UN)
                self.fh.close()
                self.l._tlock.release()

    # -- API -------------------------------------------------------------------------------------
    def total(self, state: dict | None = None) -> float:
        s = state or self._read()
        return s["settled_usd"] + sum(r["usd"] for r in s["reserved"].values())

    def can_afford(self, usd: float) -> bool:
        return self.total() + usd <= self.limit + 1e-12

    def reserve(self, usd: float, what: str = "call") -> str:
        if usd < 0:
            raise ValueError("negative reservation")
        with self._Txn(self) as s:
            if self.total(s) + usd > self.limit + 1e-12:
                raise BudgetExhausted(f"MAX_SPEND_USD={self.limit} would be exceeded by {what}: total ${self.total(s):.6f} + ${usd:.6f}")
            rid = uuid.uuid4().hex[:12]
            s["reserved"][rid] = {"usd": usd, "what": what, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            return rid

    def settle(self, rid: str, actual_usd: float) -> None:
        with self._Txn(self) as s:
            s["reserved"].pop(rid, None)
            s["settled_usd"] += max(0.0, actual_usd)

    def release(self, rid: str) -> None:
        with self._Txn(self) as s:
            s["reserved"].pop(rid, None)

    def seed(self, usd: float) -> None:
        with self._Txn(self) as s:
            s["settled_usd"] += usd

    def recover_stale(self) -> int:
        """At startup: reservations left open by a crash count as spent at their reserved (worst-case) amount."""
        with self._Txn(self) as s:
            n = len(s["reserved"])
            s["settled_usd"] += sum(r["usd"] for r in s["reserved"].values())
            s["reserved"] = {}
            return n

    def status(self) -> dict:
        s = self._read()
        return {"limit_usd": self.limit, "settled_usd": round(s["settled_usd"], 9), "reserved_usd": round(sum(r["usd"] for r in s["reserved"].values()), 9),
                "open_reservations": len(s["reserved"]), "remaining_usd": round(self.limit - self.total(s), 9)}


def main(argv=None) -> int:
    from dotenv import load_dotenv
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "seed"])
    ap.add_argument("usd", nargs="?", type=float)
    a = ap.parse_args(argv)
    ledger = Ledger(limit_usd=float(os.environ.get("MAX_SPEND_USD", "5")))
    if a.cmd == "seed":
        ledger.seed(a.usd)
    print(json.dumps(ledger.status()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
