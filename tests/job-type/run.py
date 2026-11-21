#!/usr/bin/env python3
"""Measure the job-type detector against hand-labeled Farha Google reviews.

Each JSON file is a list of [name, stars, when, label, text]; label is residential, commercial,
multifamily or unclear (unclear reviews are reported but not scored).
  python3 tests/job-type/run.py            # both sets
Pass: >= 90% correct on the clear reviews and 0 homes tagged commercial (exit code 1 otherwise)."""
import collections, glob, importlib.util, json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("mp", here.parents[1] / "farha-review-posts/scripts/make_posts.py")
mp = importlib.util.module_from_spec(spec); spec.loader.exec_module(mp)
T = ["residential", "commercial", "multifamily"]
ok_all = True
for part in ("tuning", "holdout"):
    rows = [(f.stem, n, lab, *mp.detect_job(t, n)) for f in sorted((here / part).glob("*.json"))
            for n, _, _, lab, t in json.loads(f.read_text())]
    clear = [r for r in rows if r[2] != "unclear"]
    right = sum(r[2] == r[3] for r in clear); cm = collections.Counter((r[2], r[3]) for r in clear)
    home_com = cm[("residential", "commercial")]
    print(f"\n{part}: {len(rows)} reviews, {len(clear)} clear, {right} correct = {right / len(clear):.1%}, homes tagged commercial: {home_com}")
    print(" " * 14 + "".join(f"{c[:11]:>13}" for c in T))
    for a in T: print(f"{a:14}" + "".join(f"{cm[(a, b)]:>13}" for b in T))
    for r in clear:
        if r[2] != r[3]: print(f"  MISS {r[0]} / {r[1]}: expected {r[2]}, got {r[3]} ({r[4]})")
    ok_all &= right / len(clear) >= 0.9 and home_com == 0
sys.exit(0 if ok_all else 1)
