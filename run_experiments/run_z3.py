#!/usr/bin/env python3
"""
Runs Z3 on all string_only_constraints instances and writes one CSV per
benchmark/category pair (10 total).

Usage:
    python3 run_string_only.py
    python3 run_string_only.py --base ./symcc-str-constraints/string_only_constraints
    python3 run_string_only.py --timeout 30   # seconds per instance (default: 30)
    python3 run_string_only.py --out ./results

Output (written to --out directory, default: ./results):
    b64_sat.csv, b64_unsat.csv,
    cJSON_sat.csv, cJSON_unsat.csv,
    inih_sat.csv, inih_unsat.csv,
    minicsv_sat.csv, minicsv_unsat.csv,
    yuarel_sat.csv, yuarel_unsat.csv

CSV columns:
    file_index  - 1-based index within this benchmark/category
    file_name   - e.g. symcc-assertions-0.smt2
    result      - sat | unsat | unknown | timeout | error
    runtime_ms  - wall-clock milliseconds (capped at timeout*1000 for timeouts)
    full_path   - path relative to the repo root, e.g.
                  ./string_only_constraints/yuarel/sat/symcc-assertions-0.smt2
"""

import argparse
import csv
import os
import subprocess
import tempfile
import time

BENCHMARKS = ["cJSON", "inih", "minicsv", "b64", "yuarel"]
CATEGORIES = ["sat", "unsat"]


def solve_smt2(filepath, timeout):
    """Return (verdict, runtime_ms). Strips unsupported set-option :incremental."""
    with open(filepath) as f:
        content = f.read()
    content = content.replace("(set-option :incremental true)\n", "")

    with tempfile.NamedTemporaryFile(suffix=".smt2", mode="w", delete=False) as tmp:
        tmp.write(content)
        tmppath = tmp.name

    start = time.time()
    try:
        result = subprocess.run(
            ["z3", tmppath], capture_output=True, text=True, timeout=timeout
        )
        elapsed_ms = round((time.time() - start) * 1000)
        for line in result.stdout.strip().splitlines():
            if line in ("sat", "unsat", "unknown"):
                return line, elapsed_ms
        return "error", elapsed_ms
    except subprocess.TimeoutExpired:
        return "timeout", timeout * 1000
    finally:
        os.unlink(tmppath)


def run(base_dir, out_dir, timeout):
    os.makedirs(out_dir, exist_ok=True)
    base_dir = os.path.normpath(base_dir)

    for bench in BENCHMARKS:
        for category in CATEGORIES:
            folder = os.path.join(base_dir, bench, category)
            if not os.path.isdir(folder):
                print(f"  [skip] {folder} not found")
                continue

            files = sorted(f for f in os.listdir(folder) if f.endswith(".smt2"))
            csv_path = os.path.join(out_dir, f"{bench}_{category}.csv")

            print(f"  {bench}/{category}: {len(files)} files -> {csv_path}")
            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["file_index", "file_name", "result", "runtime_ms", "full_path"])

                for idx, fname in enumerate(files, start=1):
                    fpath = os.path.join(folder, fname)
                    verdict, ms = solve_smt2(fpath, timeout)

                    repo_root = os.path.dirname(base_dir)
                    rel_path = "./" + os.path.relpath(fpath, repo_root)

                    writer.writerow([idx, fname, verdict, ms, rel_path])
                    print(f"    [{idx:>3}] {fname:<45} {verdict:<8} {ms}ms")

    print(f"\nDone. CSVs written to: {out_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--base",
        default="./symcc-str-constraints/string_only_constraints",
        help="Path to the string_only_constraints directory (default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        default="./results",
        help="Directory to write CSV files into (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Per-instance timeout in seconds (default: %(default)s)",
    )
    args = parser.parse_args()

    print(f"Base dir : {args.base}")
    print(f"Output   : {args.out}")
    print(f"Timeout  : {args.timeout}s\n")
    run(args.base, args.out, args.timeout)


if __name__ == "__main__":
    main()