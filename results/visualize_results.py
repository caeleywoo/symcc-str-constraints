#!/usr/bin/env python3
"""
visualize_results.py
Compares four solvers: cvc5, ostrich, z3-noodler, z3.
CSV format: file_name, result, runtime_ms  (no index or full_path columns)

Produces:
  plots/outcome_grid.png  — stacked bars: solved / timeout / error counts
  plots/runtime_grid.png  — log-scale avg runtime, % solved label, shared y per row
  plots/anomalies.txt     — edge cases
  plots/summary.csv       — aggregate stats

Usage:
  python3 visualize_results.py [--out-dir plots]
                               [--cvc5-dir    cvc5_results]
                               [--ostrich-dir ostrich_results]
                               [--noodler-dir z3_noodler_results]
                               [--z3-dir      z3_results]
"""

import os, csv, math, argparse
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── CLI ────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--out-dir",     default="plots")
parser.add_argument("--cvc5-dir",    default="cvc5_results")
parser.add_argument("--ostrich-dir", default="ostrich_results")
parser.add_argument("--noodler-dir", default="z3_noodler_results")
parser.add_argument("--z3-dir",      default="z3_results")
args = parser.parse_args()
os.makedirs(args.out_dir, exist_ok=True)

# ── constants ──────────────────────────────────────────────────────────────────
LIBS        = ["b64", "cJSON", "inih", "minicsv", "yuarel"]
CONSTRAINTS = ["mixed", "string_only"]
EXPECTEDS   = ["sat", "unsat"]

COLS       = [("mixed","sat"), ("mixed","unsat"),
              ("string_only","sat"), ("string_only","unsat")]
COL_TITLES = ["mixed / sat", "mixed / unsat",
              "string only / sat", "string only / unsat"]

# Solver definitions: (key, display_name, folder, bar_colour)
SOLVERS = [
    ("cvc5",    "cvc5",       args.cvc5_dir,    "#3B82F6"),  # blue
    ("ostrich", "ostrich",    args.ostrich_dir,  "#F59E0B"),  # amber
    ("z3",      "z3",         args.z3_dir,       "#A78BFA"),  # purple
    ("noodler", "z3-noodler", args.noodler_dir,  "#EF4444"),  # red
]
SOLVER_KEYS   = [s[0] for s in SOLVERS]
SOLVER_COLORS = {s[0]: s[3] for s in SOLVERS}
SOLVER_LABELS = {s[0]: s[1] for s in SOLVERS}

C = {
    "solved":  "#10B981",  # green — outcome grid
    "timeout": "#EF4444",  # red
    "error":   "#6B7280",  # grey
    "bg":      "#0F172A",
    "panel":   "#1E293B",
    "grid":    "#334155",
    "text":    "#E2E8F0",
    "sub":     "#94A3B8",
}

BAR_W    = 0.18   # width of each of the 4 bars
BAR_GAP  = 0.04   # gap between bars
# x-centres for 4 bars, centred on 0
N_BARS   = len(SOLVERS)
BAR_SPAN = N_BARS * BAR_W + (N_BARS - 1) * BAR_GAP
# offsets from centre: -1.5, -0.5, 0.5, 1.5  (times half-step)
HALF     = (BAR_W + BAR_GAP)
BAR_XS   = [(-1.5 + i) * HALF for i in range(N_BARS)]

# ── parse one CSV row ──────────────────────────────────────────────────────────
def parse_row(row):
    result = (row.get("result") or "").strip().upper()
    raw_rt = (row.get("runtime_ms") or "").strip()

    if result == "TIMEOUT":
        rc = "timeout"
    elif result == "SAT":
        rc = "sat"
    elif result == "UNSAT":
        rc = "unsat"
    else:
        # anything else (ERROR, UNKNOWN, empty, …) → error
        rc = "error"

    try:
        rt = int(raw_rt)
    except (ValueError, TypeError):
        rt = None

    # timeout wall-clock time is not a solve time
    if rc == "timeout":
        rt = None

    return {"result_class": rc, "runtime_ms": rt,
            "file_name": row.get("file_name", "")}


def load_csv(base_dir, lib, con, exp):
    path = os.path.join(base_dir, f"{lib}__{con}__{exp}.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return [parse_row(r) for r in csv.DictReader(f)]


# ── load ───────────────────────────────────────────────────────────────────────
data = {}
for key, label, base_dir, _ in SOLVERS:
    for lib in LIBS:
        for con in CONSTRAINTS:
            for exp in EXPECTEDS:
                rows = load_csv(base_dir, lib, con, exp)
                data[(key, lib, con, exp)] = rows
                status = f"{len(rows):3d} rows" if rows else "MISSING "
                print(f"  {status}  {label:12s}  {lib}/{con}/{exp}")

# ── aggregate ──────────────────────────────────────────────────────────────────
def agg(rows):
    solved_rts = [r["runtime_ms"] for r in rows
                  if r["result_class"] in ("sat", "unsat")
                  and r["runtime_ms"] is not None]
    return {
        "total":    len(rows),
        "solved":   len(solved_rts),
        "timeouts": sum(1 for r in rows if r["result_class"] == "timeout"),
        "errors":   sum(1 for r in rows if r["result_class"] == "error"),
        "mean":     float(np.mean(solved_rts))   if solved_rts else float("nan"),
        "median":   float(np.median(solved_rts)) if solved_rts else float("nan"),
        "rts":      solved_rts,
    }

stats = {}
for key, _, _, _ in SOLVERS:
    for lib in LIBS:
        for con in CONSTRAINTS:
            for exp in EXPECTEDS:
                stats[(key, lib, con, exp)] = agg(data[(key, lib, con, exp)])

# ── summary CSV ────────────────────────────────────────────────────────────────
summary_path = os.path.join(args.out_dir, "summary.csv")
with open(summary_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["solver","lib","constraints","expected",
                "total","solved","timeouts","errors","mean_ms","median_ms"])
    for key, label, _, _ in SOLVERS:
        for lib in LIBS:
            for con in CONSTRAINTS:
                for exp in EXPECTEDS:
                    s = stats[(key, lib, con, exp)]
                    w.writerow([label, lib, con, exp,
                                s["total"], s["solved"], s["timeouts"], s["errors"],
                                f"{s['mean']:.1f}", f"{s['median']:.1f}"])
print(f"\nSummary → {summary_path}")

# ── anomalies ──────────────────────────────────────────────────────────────────
anomalies = []
for lib in LIBS:
    for con in CONSTRAINTS:
        for exp in EXPECTEDS:
            cat = f"{lib}/{con}/{exp}"
            rows_by_solver = {
                key: {r["file_name"]: r for r in data[(key, lib, con, exp)]}
                for key, *_ in SOLVERS
            }
            all_files = sorted(set(
                fn for key in SOLVER_KEYS
                for fn in rows_by_solver[key]
            ))
            for fname in all_files:
                rts = {
                    key: rows_by_solver[key][fname]["runtime_ms"]
                    if fname in rows_by_solver[key] else None
                    for key in SOLVER_KEYS
                }
                cls = {
                    key: rows_by_solver[key][fname]["result_class"]
                    if fname in rows_by_solver[key] else "MISSING"
                    for key in SOLVER_KEYS
                }
                solved = [k for k in SOLVER_KEYS if cls[k] in ("sat","unsat")]
                timed  = [k for k in SOLVER_KEYS if cls[k] == "timeout"]
                # one or more time out while others solve
                if timed and solved:
                    anomalies.append(("PARTIAL_TIMEOUT", cat, fname,
                        f"timeout: {timed}  solved: {solved}"))
                # extreme ratio between any two solvers that both solved
                for i, k1 in enumerate(solved):
                    for k2 in solved[i+1:]:
                        if rts[k1] and rts[k2] and min(rts[k1],rts[k2]) > 0:
                            ratio = max(rts[k1],rts[k2]) / min(rts[k1],rts[k2])
                            if ratio >= 10:
                                faster = k1 if rts[k1] < rts[k2] else k2
                                anomalies.append(("EXTREME_RATIO", cat, fname,
                                    f"{faster} is {ratio:.0f}× faster "
                                    f"({k1}={rts[k1]}ms, {k2}={rts[k2]}ms)"))

anomaly_path = os.path.join(args.out_dir, "anomalies.txt")
with open(anomaly_path, "w") as f:
    f.write("ANOMALY REPORT\n" + "="*70 + "\n\n")
    by_type = defaultdict(list)
    for a in anomalies: by_type[a[0]].append(a)
    for atype, items in by_type.items():
        f.write(f"── {atype}  ({len(items)}) ──\n")
        for _, cat, fname, note in items:
            f.write(f"  [{cat}]  {fname}\n    {note}\n")
        f.write("\n")
    if not anomalies:
        f.write("No anomalies detected.\n")
print(f"Anomalies → {anomaly_path}  ({len(anomalies)} found)")

# ── shared helpers ─────────────────────────────────────────────────────────────
def style_ax(ax, n_bars=N_BARS):
    ax.set_facecolor(C["panel"])
    for sp in ax.spines.values():
        sp.set_edgecolor(C["grid"])
    ax.tick_params(axis="both", colors=C["sub"], labelsize=8)
    ax.grid(axis="y", color=C["grid"], linewidth=0.5, zorder=1)
    ax.set_xticks(BAR_XS)
    ax.set_xticklabels([SOLVER_LABELS[k] for k in SOLVER_KEYS],
                       color="white", fontsize=13, rotation=15, ha="right")
    ax.set_xlim(BAR_XS[0] - BAR_W, BAR_XS[-1] + BAR_W)

def make_grid():
    fig, axes = plt.subplots(len(LIBS), len(COLS),
                              figsize=(36, len(LIBS) * 5.5), squeeze=False)
    fig.patch.set_facecolor(C["bg"])
    for ci, title in enumerate(COL_TITLES):
        axes[0][ci].set_title(title, color=C["text"], fontsize=36,
                               fontweight="bold", pad=18)
    for ri, lib in enumerate(LIBS):
        axes[ri][0].set_ylabel(lib, color=C["text"], fontsize=34,
                                fontweight="bold", rotation=0,
                                labelpad=100, va="center")
    return fig, axes

# ═══════════════════════════════════════════════════════════════════════════════
# GRID 1 — outcome breakdown (solved / timeout / error)
# colours: green = solved, red = timeout, grey = error/unknown
# labels:  percentage of total (excl. missing)
# ═══════════════════════════════════════════════════════════════════════════════
OUTCOME_COLORS = {
    "solved":  "#22C55E",  # green
    "timeout": "#EF4444",  # red
    "error":   "#6B7280",  # grey
}

fig1, axes1 = make_grid()

for ri, lib in enumerate(LIBS):
    for ci, (con, exp) in enumerate(COLS):
        ax = axes1[ri][ci]
        style_ax(ax)

        for xi, (key, label, _, _) in zip(BAR_XS, SOLVERS):
            s     = stats[(key, lib, con, exp)]
            total = s["total"]
            if total == 0:
                ax.text(xi, 0.5, "N/A", ha="center", va="center",
                        color=C["sub"], fontsize=13)
                continue
            bottom = 0
            for count, seg_key in [
                (s["solved"],   "solved"),
                (s["timeouts"], "timeout"),
                (s["errors"],   "error"),
            ]:
                if count:
                    color = OUTCOME_COLORS[seg_key]
                    ax.bar(xi, count, bottom=bottom, width=BAR_W,
                           color=color, alpha=0.88, zorder=2)
                    pct = count / total * 100
                    ax.text(xi, bottom + count / 2, f"{pct:.0f}%",
                            ha="center", va="center",
                            color="white", fontsize=18, fontweight="bold", zorder=4)
                    bottom += count

fig1.legend(handles=[
    mpatches.Patch(color=OUTCOME_COLORS["solved"],  label="solved"),
    mpatches.Patch(color=OUTCOME_COLORS["timeout"], label="timeout"),
    mpatches.Patch(color=OUTCOME_COLORS["error"],   label="error / unknown"),
], loc="lower center", ncol=3, frameon=False, fontsize=36,
   labelcolor="white", bbox_to_anchor=(0.5, 0.002))

fig1.suptitle(
    "Outcome breakdown — cvc5 / ostrich / z3-noodler / z3\n"
    "bars = % of files  ·  green = solved  ·  red = timeout  ·  grey = error/unknown",
    color=C["text"], fontsize=40, fontweight="bold", y=1.005)
plt.tight_layout(rect=[0.10, 0.06, 1, 1])
p1 = os.path.join(args.out_dir, "outcome_grid.png")
fig1.savefig(p1, dpi=150, bbox_inches="tight", facecolor=C["bg"])
plt.close(fig1)
print(f"Outcome grid → {p1}")


# ═══════════════════════════════════════════════════════════════════════════════
# GRID 2 — average solve time (log scale, shared y per row)
# bar height  = mean runtime of solved files
# % label     = solved / (solved + timeout)  [errors excluded]
# y-axis      = same limits across all 4 cells in a row
# ═══════════════════════════════════════════════════════════════════════════════
fig2, axes2 = make_grid()

LOG_FLOOR = 10   # ms

def fmt_ms(v, _=None):
    if v >= 60_000: return f"{v/60000:.0f}min"
    if v >= 1_000:  return f"{v/1000:.0f}s"
    return f"{v:.0f}ms"

def nice_log_ticks(ymin, ymax):
    candidates = []
    for exp in range(0, 7):
        for mult in (1, 2, 5):
            v = mult * (10 ** exp)
            if ymin * 0.85 <= v <= ymax * 1.15:
                candidates.append(v)
    return sorted(set(candidates)) or [ymin, ymax]

# first pass: per-row y range (all 4 cols × 4 solvers = 16 means)
row_ymin, row_ymax = {}, {}
for ri, lib in enumerate(LIBS):
    all_means = [
        stats[(key, lib, con, exp)]["mean"]
        for con, exp in COLS
        for key in SOLVER_KEYS
        if not math.isnan(stats[(key, lib, con, exp)]["mean"])
        and stats[(key, lib, con, exp)]["mean"] > 0
    ]
    row_ymin[ri] = max(LOG_FLOOR, min(all_means) * 0.4) if all_means else LOG_FLOOR
    row_ymax[ri] = max(all_means) * 4.5                  if all_means else LOG_FLOOR * 100

# second pass: draw
for ri, lib in enumerate(LIBS):
    ymin   = row_ymin[ri]
    ymax   = row_ymax[ri]
    ticks  = nice_log_ticks(ymin, ymax)

    for ci, (con, exp) in enumerate(COLS):
        ax = axes2[ri][ci]
        style_ax(ax)
        ax.set_yscale("log")
        ax.set_ylim(ymin, ymax)
        ax.set_yticks(ticks)
        if ci == 0:
            ax.set_yticklabels([fmt_ms(v) for v in ticks],
                               color=C["sub"], fontsize=7.5)
        else:
            ax.set_yticklabels([])
        ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())

        for xi, (key, label, _, color) in zip(BAR_XS, SOLVERS):
            s        = stats[(key, lib, con, exp)]
            mean     = s["mean"]
            n_solved = s["solved"]
            n_timed  = s["timeouts"]
            denom    = n_solved + n_timed
            pct      = (n_solved / denom * 100) if denom > 0 else 0.0

            if math.isnan(mean) or n_solved == 0:
                ax.bar(xi, ymin * 1.5, width=BAR_W, color=color,
                       alpha=0.18, zorder=2)
                ax.text(xi, ymin * 1.9, "0%",
                        ha="center", va="bottom",
                        color=C["sub"], fontsize=18, fontweight="bold", zorder=4)
                continue

            ax.bar(xi, mean, width=BAR_W, color=color, alpha=0.85, zorder=2)

            # runtime label above bar
            ax.text(xi, mean * 1.2, fmt_ms(mean),
                    ha="center", va="bottom",
                    color="white", fontsize=18, fontweight="bold", zorder=4)

            # % solved label at log-midpoint inside bar
            mid = math.exp((math.log(ymin) + math.log(mean)) / 2)
            ax.text(xi, mid, f"{pct:.0f}%",
                    ha="center", va="center",
                    color="white", fontsize=18, fontweight="bold",
                    alpha=0.95, zorder=4)

fig2.legend(handles=[
    mpatches.Patch(color=SOLVER_COLORS[key], label=SOLVER_LABELS[key])
    for key in SOLVER_KEYS
], loc="lower center", ncol=4, frameon=False, fontsize=36,
   labelcolor="white", bbox_to_anchor=(0.5, 0.002))

fig2.suptitle(
    "Average solve time — cvc5 / ostrich / z3-noodler / z3  (log scale, solved files only)\n"
    "bar = mean runtime  ·  % inside = solved ÷ (solved + timeout)  ·  y-axis shared within each row",
    color=C["text"], fontsize=40, fontweight="bold", y=1.005)
plt.tight_layout(rect=[0.10, 0.06, 1, 1])
p2 = os.path.join(args.out_dir, "runtime_grid.png")
fig2.savefig(p2, dpi=150, bbox_inches="tight", facecolor=C["bg"])
plt.close(fig2)
print(f"Runtime grid → {p2}")

print("\nDone. Files in:", args.out_dir + "/")
