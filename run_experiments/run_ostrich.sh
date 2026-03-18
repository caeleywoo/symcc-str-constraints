#!/bin/bash

OSTRICH_JAR=~/ostrich2/ostrich-2.0.1/target/scala-2.11/ostrich-assembly-2.0.1.jar
TIMEOUT=60
OUTPUT=~/benchmark_constraints/ostrich_results.csv
PROGRAMS="cJSON inih b64 minicsv yuarel"

echo "program,file,type,result,time_ms" > $OUTPUT

total=$(find ~/benchmark_constraints -name "*.smt2" | wc -l)
count=0

for program in $PROGRAMS; do
    for type in sat unsat; do
        dir=~/benchmark_constraints/$program/$type
        for f in $dir/*.smt2; do
            [ -f "$f" ] || continue
            count=$((count + 1))
            filename=$(basename "$f")

            start=$(date +%s%3N)
            output=$(timeout ${TIMEOUT}s java -jar $OSTRICH_JAR "$f" 2>&1)
            exit_code=$?
            end=$(date +%s%3N)
            elapsed=$((end - start))

            if [ $exit_code -eq 124 ]; then
                result="timeout"
            else
                result=$(echo "$output" | grep -E "^(sat|unsat|unknown)$" | tail -1)
                [ -z "$result" ] && result="unknown"
            fi

            echo "$program,$filename,$type,$result,$elapsed" >> $OUTPUT
            echo "[$count/$total] $program/$type/$filename: $result (${elapsed}ms)"
        done
    done

    echo "--- $program complete ---"
    grep "^$program," $OUTPUT | awk -F',' '{print $4}' | sort | uniq -c
done

echo ""
echo "=== FINAL SUMMARY ==="
for program in $PROGRAMS; do
    echo "-- $program --"
    grep "^$program," $OUTPUT | awk -F',' '{print $4}' | sort | uniq -c
done
echo "Results saved to $OUTPUT"
