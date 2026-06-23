"""Compare two JSONL result files from the post-training tests."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from eval_utils import read_jsonl, row_passes


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--name-a", default="a")
    ap.add_argument("--name-b", default="b")
    ap.add_argument("--character", required=True, choices=["elysia", "cyrene"])
    ap.add_argument("--out", required=True)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    a_rows = read_jsonl(args.a)
    b_rows = read_jsonl(args.b)

    a_map = {(r.get("id"), r.get("repeat", 1)): r for r in a_rows}
    b_map = {(r.get("id"), r.get("repeat", 1)): r for r in b_rows}

    keys = sorted(set(a_map) & set(b_map))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    improved = worsened = same = 0

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "id", "repeat", "category", "language", "prompt",
            f"{args.name_a}_pass", f"{args.name_b}_pass",
            f"{args.name_a}_chars", f"{args.name_b}_chars",
            f"{args.name_a}_response", f"{args.name_b}_response",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for key in keys:
            ra = a_map[key]
            rb = b_map[key]
            pa = row_passes(ra, args.character)
            pb = row_passes(rb, args.character)

            if pa == pb:
                same += 1
            elif pb and not pa:
                improved += 1
            elif pa and not pb:
                worsened += 1

            w.writerow({
                "id": key[0],
                "repeat": key[1],
                "category": ra.get("category"),
                "language": ra.get("language"),
                "prompt": ra.get("prompt"),
                f"{args.name_a}_pass": pa,
                f"{args.name_b}_pass": pb,
                f"{args.name_a}_chars": ra.get("checks", {}).get("char_count"),
                f"{args.name_b}_chars": rb.get("checks", {}).get("char_count"),
                f"{args.name_a}_response": ra.get("response"),
                f"{args.name_b}_response": rb.get("response"),
            })

    print("Compared:", len(keys))
    print("Improved:", improved)
    print("Worsened:", worsened)
    print("Same:", same)
    print("Wrote:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
