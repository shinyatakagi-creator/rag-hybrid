"""python -m api.dryrun [--query "..."]   cost estimate for ONE live /search and ONE live /ask. Makes no paid call.

/search: only the query embedding costs anything (bm25 is free). /ask: query embedding + one answer call + one verification call.
Typical figures come from the measured answer_eval run (usage fields in eval/results/answer_eval_*.jsonl); worst cases are what the
ledger would reserve before each call.
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from api.ledger import Ledger
from ingest.embed_cache import cost_usd as embed_cost, count_tokens
from rag import generate as G
from rag import verify as V
from rag.query_cache import QueryCache, serving_path
from ingest.embed_cache import cache_key


def measured() -> dict:
    gens = [json.loads(l) for l in open("eval/results/answer_eval_generation.jsonl", encoding="utf8")]
    vers = [json.loads(l) for l in open("eval/results/answer_eval_verification.jsonl", encoding="utf8") if '"usage"' in l]
    ans = [g for g in gens if "answer" in g and g["answer"]["answerable"]]
    avg = lambda rows, k: sum(r["usage"][k] for r in rows) / len(rows)
    return {"gen_in": avg(gens, "input_tokens"), "gen_out_answered": avg(ans, "output_tokens"), "ver_in": avg(vers, "input_tokens"), "ver_out": avg(vers, "output_tokens"),
            "n_gen": len(gens), "n_ans": len(ans), "n_ver": len(vers)}


def main(argv=None) -> int:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="How do I safely drain a node for maintenance?")
    a = ap.parse_args(argv)
    am, vm = os.environ["ANSWER_MODEL"], os.environ["VERIFIER_MODEL"]
    em = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
    m = measured()
    cached = QueryCache(serving_path(f"data/embed_cache/{em}.jsonl")).has(cache_key(em, 1536, a.query))
    qt = count_tokens(a.query)
    e_cost = 0.0 if cached else embed_cost(em, qt)
    ledger = Ledger(limit_usd=float(os.environ.get("MAX_SPEND_USD", "5")))
    st = ledger.status()
    gen_typ = G.cost_usd(am, int(m["gen_in"]), int(m["gen_out_answered"]))
    gen_worst = G.cost_usd(am, int(m["gen_in"]), G.MAX_TOKENS)
    ver_typ = G.cost_usd(vm, int(m["ver_in"]), int(m["ver_out"]))
    ver_worst = G.cost_usd(vm, int(m["ver_in"]), V.MAX_TOKENS)
    print(f"Query: {a.query!r} ({qt} tokens; already in the serving cache: {cached})\n"
          f"Ledger: {json.dumps(st)}\n\n"
          f"POST /search  (mode dense or hybrid; bm25 is free)\n"
          f"  query embedding {embed_cost(em, qt) if not cached else 0:.8f} USD  ({em}, {qt} tokens; $0 if the query is cached)\n"
          f"  ledger reserves this amount before the call and settles to the API-reported usage\n\n"
          f"POST /ask\n"
          f"  query embedding        {e_cost:.8f} USD\n"
          f"  answer  ({am}, effort {G.EFFORT}): typical ${gen_typ:.4f}  (measured mean over {m['n_gen']} calls in answer_eval: {m['gen_in']:.0f} in / {m['gen_out_answered']:.0f} out tokens for an answer)\n"
          f"                         reserved before the call (worst case, {G.MAX_TOKENS}-token output ceiling): ${gen_worst:.4f}\n"
          f"  verify  ({vm}, {V.RUBRIC}, effort {V.EFFORT}): typical ${ver_typ:.4f}  (measured mean over {m['n_vers'] if 'n_vers' in m else m['n_ver']} calls: {m['ver_in']:.0f} in / {m['ver_out']:.0f} out)\n"
          f"                         reserved before the call (worst case, {V.MAX_TOKENS}-token output ceiling): ${ver_worst:.4f}\n"
          f"  total typical ${e_cost + gen_typ + ver_typ:.4f}; peak amount held at once about ${gen_worst + e_cost:.4f} (then ${ver_worst:.4f} for verification); absolute worst case ${e_cost + gen_worst + ver_worst:.4f}\n"
          f"  a refusal skips verification: about ${e_cost + G.cost_usd(am, int(m['gen_in']), 70):.4f}\n\n"
          f"The estimates are not API calls. Nothing was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
