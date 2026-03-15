#!/usr/bin/env python3
"""
visualize_results.py
Compares cvc5 vs z3-noodler benchmark results.
Produces two 5x4 grids:
  1. outcome_grid.png  — stacked bars: solved / timeout / error counts
  2. runtime_grid.png  — avg runtime of solved files, labelled with solve count

Usage:
  python3 visualize_results.py [--cvc5-dir cvc5_results] [--noodler-dir z3_noodler_results] [--out-dir plots]
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
parser.add_argument("--cvc5-dir",    default="cvc5_results")
parser.add_argument("--noodler-dir", default="noodler_results")
parser.add_argument("--out-dir",     default="plots")
args = parser.parse_args()
os.makedirs(args.out_dir, exist_ok=True)

LIBS        = ["b64", "cJSON", "inih", "minicsv", "yuarel"]
CONSTRAINTS = ["mixed", "string_only"]
EXPECTEDS   = ["sat", "unsat"]
SOLVERS     = [("cvc5", args.cvc5_dir), ("noodler", args.noodler_dir)]

COLS       = [("mixed","sat"), ("mixed","unsat"),
              ("string_only","sat"), ("string_only","unsat")]
COL_TITLES = ["mixed / sat", "mixed / unsat",
              "string only / sat", "string only / unsat"]

C = {
    "cvc5":    "#3B82F6",   # blue  — used in runtime grid
    "noodler": "#EF4444",   # red   — used in runtime grid
    "solved":  "#10B981",   # green — used in outcome grid (same for both solvers)
    "timeout": "#F59E0B",   # amber
    "error":   "#8B5CF6",   # purple
    "bg":      "#0F172A",
    "panel":   "#1E293B",
    "grid":    "#334155",
    "text":    "#E2E8F0",
    "sub":     "#94A3B8",
}

# ── parse ──────────────────────────────────────────────────────────────────────
def parse_row(row):
    result = (row.get("result") or "").strip().upper()
    raw_rt = (row.get("runtime_ms") or "").strip()
    if result == "TIMEOUT":
        rc = "timeout"
    elif result.startswith("ERROR") or result in ("UNKNOWN", ""):
        rc = "error"
    elif result == "SAT":
        rc = "sat"
    elif result == "UNSAT":
        rc = "unsat"
    else:
        rc = "error"
    try:
        rt = int(raw_rt)
    except (ValueError, TypeError):
        rt = None
    # don't count timeout wall-clock times as solve times
    if rc == "timeout":
        rt = None
    return {"result_class": rc, "runtime_ms": rt, "file_name": row.get("file_name", "")}

def load_csv(base_dir, lib, con, exp):
    path = os.path.join(base_dir, f"{lib}__{con}__{exp}.csv")
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return [parse_row(r) for r in csv.DictReader(f)]

# ── load ───────────────────────────────────────────────────────────────────────
data = {}
for solver, base_dir in SOLVERS:
    for lib in LIBS:
        for con in CONSTRAINTS:
            for exp in EXPECTEDS:
                rows = load_csv(base_dir, lib, con, exp)
                data[(solver, lib, con, exp)] = rows
                status = f"{len(rows):3d} rows" if rows else "MISSING "
                print(f"  {status}  {solver:8s}  {lib}/{con}/{exp}")

# ── aggregate ──────────────────────────────────────────────────────────────────
def agg(rows):
    solved_rts = [r["runtime_ms"] for r in rows
                  if r["result_class"] in ("sat","unsat")
                  and r["runtime_ms"] is not None]
    return {
        "total":    len(rows),
        "solved":   len(solved_rts),
        "timeouts": sum(1 for r in rows if r["result_class"] == "timeout"),
        "errors":   sum(1 for r in rows if r["result_class"] == "error"),
        "mean":     float(np.mean(solved_rts))   if solved_rts else float("nan"),
        "median":   float(np.median(solved_rts)) if solved_rts else float("nan"),
    }

stats = {}
for solver, _ in SOLVERS:
    for lib in LIBS:
        for con in CONSTRAINTS:
            for exp in EXPECTEDS:
                stats[(solver, lib, con, exp)] = agg(data[(solver, lib, con, exp)])

# ── anomalies ──────────────────────────────────────────────────────────────────
anomalies = []
for lib in LIBS:
    for con in CONSTRAINTS:
        for exp in EXPECTEDS:
            cat = f"{lib}/{con}/{exp}"
            rc_rows = {r["file_name"]: r for r in data[("cvc5",    lib, con, exp)]}
            rn_rows = {r["file_name"]: r for r in data[("noodler", lib, con, exp)]}
            for fname in sorted(set(list(rc_rows) + list(rn_rows))):
                rc = rc_rows.get(fname)
                rn = rn_rows.get(fname)
                def cls(r): return r["result_class"] if r else "MISSING"
                def rt(r):  return r["runtime_ms"]   if r else None
                if cls(rc) == "timeout" and cls(rn) in ("sat","unsat"):
                    anomalies.append(("CVC5_TIMEOUT_NOODLER_OK", cat, fname,
                        f"cvc5 timed out; noodler={cls(rn)} in {rt(rn)}ms"))
                if cls(rn) == "timeout" and cls(rc) in ("sat","unsat"):
                    anomalies.append(("NOODLER_TIMEOUT_CVC5_OK", cat, fname,
                        f"noodler timed out; cvc5={cls(rc)} in {rt(rc)}ms"))
                if (rt(rc) and rt(rn) and
                    cls(rc) in ("sat","unsat") and cls(rn) in ("sat","unsat")):
                    ratio = max(rt(rc), rt(rn)) / min(rt(rc), rt(rn))
                    if ratio >= 10:
                        faster = "cvc5" if rt(rc) < rt(rn) else "noodler"
                        anomalies.append(("EXTREME_RATIO", cat, fname,
                            f"{faster} is {ratio:.0f}× faster "
                            f"(cvc5={rt(rc)}ms, noodler={rt(rn)}ms)"))

anomaly_path = os.path.join(args.out_dir, "anomalies.txt")
type_labels = {
    "CVC5_TIMEOUT_NOODLER_OK": "cvc5 timed out, noodler solved it",
    "NOODLER_TIMEOUT_CVC5_OK": "noodler timed out, cvc5 solved it",
    "EXTREME_RATIO":           "Extreme runtime ratio (≥10×)",
}
with open(anomaly_path, "w") as f:
    f.write("ANOMALY REPORT\n" + "="*70 + "\n\n")
    by_type = defaultdict(list)
    for a in anomalies: by_type[a[0]].append(a)
    for atype, label in type_labels.items():
        items = by_type.get(atype, [])
        f.write(f"── {label}  ({len(items)}) ──\n")
        for _, cat, fname, note in items:
            f.write(f"  [{cat}]  {fname}\n    {note}\n")
        f.write("\n")
    if not anomalies:
        f.write("No anomalies detected.\n")
print(f"\nAnomalies → {anomaly_path}  ({len(anomalies)} found)")

# ── shared axis setup ──────────────────────────────────────────────────────────
def style_ax(ax):
    ax.set_facecolor(C["panel"])
    for sp in ax.spines.values():
        sp.set_edgecolor(C["grid"])
    ax.tick_params(axis="both", colors=C["sub"], labelsize=8)
    ax.grid(axis="y", color=C["grid"], linewidth=0.5, zorder=1)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["cvc5", "noodler"], color=C["sub"], fontsize=9)
    ax.set_xlim(-0.6, 1.6)

def make_grid(figsize=(22, len(LIBS)*3.8)):
    fig, axes = plt.subplots(len(LIBS), len(COLS), figsize=figsize, squeeze=False)
    fig.patch.set_facecolor(C["bg"])
    for ci, title in enumerate(COL_TITLES):
        axes[0][ci].set_title(title, color=C["text"], fontsize=15,
                               fontweight="bold", pad=12)
    for ri, lib in enumerate(LIBS):
        axes[ri][0].set_ylabel(lib, color=C["text"], fontsize=14,
                                fontweight="bold", rotation=0,
                                labelpad=65, va="center")
    return fig, axes

# ═══════════════════════════════════════════════════════════════════════════════
# GRID 1 — outcome breakdown (solved / timeout / error)
# solved = same green regardless of solver
# ═══════════════════════════════════════════════════════════════════════════════
fig1, axes1 = make_grid()

for ri, lib in enumerate(LIBS):
    for ci, (con, exp) in enumerate(COLS):
        ax = axes1[ri][ci]
        style_ax(ax)

        for xi, (solver, _) in enumerate(SOLVERS):
            s = stats[(solver, lib, con, exp)]
            if s["total"] == 0:
                ax.text(xi, 0.5, "no data", ha="center", va="center",
                        color=C["sub"], fontsize=7)
                continue

            bottom = 0
            for count, color in [
                (s["solved"],   C["solved"]),
                (s["timeouts"], C["timeout"]),
                (s["errors"],   C["error"]),
            ]:
                if count:
                    ax.bar(xi, count, bottom=bottom, width=0.55,
                           color=color, alpha=0.88, zorder=2)
                    ax.text(xi, bottom + count / 2, str(count),
                            ha="center", va="center",
                            color="white", fontsize=8, fontweight="bold", zorder=4)
                    bottom += count

fig1.legend(handles=[
    mpatches.Patch(color=C["solved"],  label="solved"),
    mpatches.Patch(color=C["timeout"], label="timeout"),
    mpatches.Patch(color=C["error"],   label="error"),
], loc="lower center", ncol=3, frameon=False, fontsize=11,
   labelcolor=C["text"], bbox_to_anchor=(0.5, 0.002))

fig1.suptitle(
    "Outcome breakdown — cvc5 vs z3-noodler\n"
    "bars = # files solved (green) / timed out (amber) / errored (purple)",
    color=C["text"], fontsize=17, fontweight="bold", y=1.005)
plt.tight_layout(rect=[0.07, 0.04, 1, 1])
p1 = os.path.join(args.out_dir, "outcome_grid.png")
fig1.savefig(p1, dpi=150, bbox_inches="tight", facecolor=C["bg"])
plt.close(fig1)
print(f"Outcome grid → {p1}")


# ═══════════════════════════════════════════════════════════════════════════════
# GRID 2 — average solve time (log scale, shared y-axis per row)
# bar height  = mean runtime of solved files
# % label     = solved / (solved + timeout)  [errors excluded]
# y-axis      = same limits across all 4 cells in a row
# ═══════════════════════════════════════════════════════════════════════════════
fig2, axes2 = make_grid()

bar_w     = 0.55
LOG_FLOOR = 10   # ms floor so log axis doesn't blow up on tiny values

def fmt_ms(v, _):
    """Human-readable ms/s/min tick labels."""
    if v >= 60_000: return f"{v/60000:.0f}min"
    if v >= 1_000:  return f"{v/1000:.0f}s"
    return f"{v:.0f}ms"

def nice_log_ticks(ymin, ymax):
    """Return a list of round tick values that span [ymin, ymax] on a log scale."""
    import math as _math
    candidates = []
    # powers of 10 between 1ms and 10min
    for exp in range(0, 7):          # 1ms … 1000s
        for mult in (1, 2, 5):
            v = mult * (10 ** exp)
            if ymin * 0.9 <= v <= ymax * 1.1:
                candidates.append(v)
    return sorted(set(candidates)) or [ymin, ymax]

# ── first pass: find per-row y range across all 8 means (4 cols × 2 solvers) ──
row_ymax = {}
row_ymin = {}
for ri, lib in enumerate(LIBS):
    all_means = [
        stats[(solver, lib, con, exp)]["mean"]
        for con, exp in COLS
        for solver, _ in SOLVERS
        if not math.isnan(stats[(solver, lib, con, exp)]["mean"])
        and stats[(solver, lib, con, exp)]["mean"] > 0
    ]
    row_ymin[ri] = max(LOG_FLOOR, min(all_means) * 0.4) if all_means else LOG_FLOOR
    row_ymax[ri] = max(all_means) * 4.0                  if all_means else LOG_FLOOR * 100

# ── second pass: draw ──────────────────────────────────────────────────────────
for ri, lib in enumerate(LIBS):
    ymin = row_ymin[ri]
    ymax = row_ymax[ri]
    ticks = nice_log_ticks(ymin, ymax)

    for ci, (con, exp) in enumerate(COLS):
        ax = axes2[ri][ci]
        style_ax(ax)
        ax.set_yscale("log")
        ax.set_ylim(ymin, ymax)

        # set shared ticks — labels only on leftmost column
        ax.set_yticks(ticks)
        if ci == 0:
            ax.set_yticklabels([fmt_ms(v, None) for v in ticks],
                               color=C["sub"], fontsize=7.5)
        else:
            ax.set_yticklabels([])
        ax.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())

        for xi, (solver, color) in enumerate([("cvc5",    C["cvc5"]),
                                               ("noodler", C["noodler"])]):
            s        = stats[(solver, lib, con, exp)]
            mean     = s["mean"]
            n_solved = s["solved"]
            n_timed  = s["timeouts"]
            denom    = n_solved + n_timed   # errors excluded from pct
            pct      = (n_solved / denom * 100) if denom > 0 else 0.0

            if math.isnan(mean) or n_solved == 0:
                # ghost stub at floor so bar is visible, with "0%" tag
                ax.bar(xi, ymin * 1.5, width=bar_w, color=color,
                       alpha=0.18, zorder=2)
                ax.text(xi, ymin * 1.8, "0%",
                        ha="center", va="bottom",
                        color=C["sub"], fontsize=8, fontweight="bold", zorder=4)
                continue

            ax.bar(xi, mean, width=bar_w, color=color, alpha=0.85, zorder=2)

            # runtime label just above the bar
            rt_label = fmt_ms(mean, None)
            ax.text(xi, mean * 1.18, rt_label,
                    ha="center", va="bottom",
                    color="white", fontsize=8, fontweight="bold", zorder=4)

            # % solved label inside the bar (mid-height on log scale)
            mid = math.exp((math.log(ymin) + math.log(mean)) / 2)
            ax.text(xi, mid, f"{pct:.0f}%",
                    ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold",
                    alpha=0.95, zorder=4)

fig2.legend(handles=[
    mpatches.Patch(color=C["cvc5"],    label="cvc5"),
    mpatches.Patch(color=C["noodler"], label="z3-noodler"),
], loc="lower center", ncol=2, frameon=False, fontsize=11,
   labelcolor=C["text"], bbox_to_anchor=(0.5, 0.002))

fig2.suptitle(
    "Average solve time — cvc5 vs z3-noodler  (log scale, solved files only)\n"
    "bar = mean runtime  ·  % inside = solved ÷ (solved + timeout)  ·  y-axis shared within each row",
    color=C["text"], fontsize=17, fontweight="bold", y=1.005)
plt.tight_layout(rect=[0.07, 0.04, 1, 1])
p2 = os.path.join(args.out_dir, "runtime_grid.png")
fig2.savefig(p2, dpi=150, bbox_inches="tight", facecolor=C["bg"])
plt.close(fig2)
print(f"Runtime grid → {p2}")

print("\nDone. Files in:", args.out_dir + "/")
