#!/usr/bin/env bash
# run_cvc5_benchmark.sh
# Runs cvc5 on ALL files in a single specified folder.
# Results are written to cvc5_results/<lib>__<constraints>__<expected>.csv
#
# Usage:  ./run_cvc5_benchmark.sh <lib>/<constraints>/<expected> [base_dir]
#   e.g.  ./run_cvc5_benchmark.sh cJSON/mixed/unsat
#         ./run_cvc5_benchmark.sh b64/string_only/sat /path/to/root
#
# <constraints> must be either "mixed" or "string_only"
# <expected>    must be either "sat" or "unsat"
#
# Compatible with bash 3.2+ (macOS default)

TIMEOUT=300
FOLDER_ARG="${1:-}"
BASE_DIR="${2:-.}"
OUT_DIR="cvc5_results"

if [ -z "$FOLDER_ARG" ]; then
    echo "Usage: $0 <lib>/<constraints>/<expected> [base_dir]" >&2
    echo "  e.g. $0 cJSON/mixed/unsat" >&2
    echo "  e.g. $0 b64/string_only/sat /path/to/root" >&2
    exit 1
fi

# Parse the argument
lib=$(echo "$FOLDER_ARG"        | cut -d'/' -f1)
sonly_slug=$(echo "$FOLDER_ARG" | cut -d'/' -f2)
expected=$(echo "$FOLDER_ARG"   | cut -d'/' -f3)

# Validate
case "$sonly_slug" in
    mixed)       sonly_label="mixed" ;;
    string_only) sonly_label="string only" ;;
    *)
        echo "Error: constraints must be 'mixed' or 'string_only', got: '$sonly_slug'" >&2
        exit 1 ;;
esac

case "$expected" in
    sat|unsat) ;;
    *)
        echo "Error: expected must be 'sat' or 'unsat', got: '$expected'" >&2
        exit 1 ;;
esac

# Resolve the actual directory on disk
if [ "$sonly_slug" = "string_only" ]; then
    subdir="$BASE_DIR/string_only_constraints/${lib}/${expected}"
else
    subdir="$BASE_DIR/${lib}/${expected}"
fi

if [ ! -d "$subdir" ]; then
    echo "Error: directory not found: $subdir" >&2
    exit 1
fi

ms_now() { python3 -c "import time; print(int(time.time() * 1000))"; }

run_one() {
    local smt_file="$1" output exit_code first_line t0 t1
    t0=$(ms_now)
    output=$(timeout "$TIMEOUT" cvc5 --lang=smt2 "$smt_file" 2>&1)
    exit_code=$?
    t1=$(ms_now)
    ELAPSED_MS=$(( t1 - t0 ))

    if [ $exit_code -eq 124 ]; then
        RESULT="TIMEOUT"
    elif [ $exit_code -ne 0 ] && [ $exit_code -ne 10 ] && [ $exit_code -ne 20 ]; then
        RESULT="ERROR($exit_code)"
    else
        first_line=$(printf '%s\n' "$output" | grep -m1 -E '^(sat|unsat|unknown)')
        case "$first_line" in
            sat)   RESULT="sat"     ;;
            unsat) RESULT="unsat"   ;;
            *)     RESULT="unknown" ;;
        esac
    fi
}

# ── setup ──────────────────────────────────────────────────────────────────────
mkdir -p "$OUT_DIR"

csv="$OUT_DIR/${lib}__${sonly_slug}__${expected}.csv"
disagree_file="$OUT_DIR/${lib}__${sonly_slug}__${expected}__disagreements.txt"
disagree_count=0

# Write CSV header (overwrite any existing file)
printf 'file_index,file_name,result,runtime_ms,full_path\n' > "$csv"
printf 'SOLVER DISAGREEMENTS — %s / %s / %s\n' "$lib" "$sonly_label" "$expected" > "$disagree_file"
printf 'Files where solver result != folder label.\n(Timeouts/errors/unknowns excluded.)\n\n' >> "$disagree_file"

echo "▶ Running: ${lib} / ${sonly_label} / ${expected}" >&2
echo "  Source dir : $subdir" >&2
echo "  Output CSV : $csv" >&2
echo "  Timeout    : ${TIMEOUT}s per file" >&2
echo "" >&2

# ── run all files in the folder ────────────────────────────────────────────────
idx=0
while IFS= read -r smt_file; do
    idx=$(( idx + 1 ))
    fname="$(basename "$smt_file")"

    echo "  #${idx}  ${fname}" >&2
    run_one "$smt_file"
    echo "       → ${RESULT}  ${ELAPSED_MS}ms" >&2

    printf '%s,%s,%s,%s,%s\n' \
        "$idx" "$fname" "$RESULT" "$ELAPSED_MS" "$smt_file" >> "$csv"

    if [ "$RESULT" != "$expected" ] && \
       [ "$RESULT" != "TIMEOUT" ]   && \
       [ "$RESULT" != "unknown" ]   && \
       ! echo "$RESULT" | grep -q "^ERROR"; then
        printf 'File #%s : %s\n'        "$idx" "$smt_file"  >> "$disagree_file"
        printf 'Expected : %s\n'        "$expected"          >> "$disagree_file"
        printf 'Got      : %s (%sms)\n\n' "$RESULT" "$ELAPSED_MS" >> "$disagree_file"
        disagree_count=$(( disagree_count + 1 ))
    fi

done < <(ls "$subdir"/*.smt2 2>/dev/null | sort -t'-' -k1,1 -k2,2n)

if [ $disagree_count -eq 0 ]; then
    printf 'None — all definitive results matched the folder label.\n' >> "$disagree_file"
fi

echo "" >&2
echo "════════════════════════════════════" >&2
echo "Done." >&2
echo "CSV written to    : $csv" >&2
echo "Disagreements     : $disagree_file  ($disagree_count found)" >&2
