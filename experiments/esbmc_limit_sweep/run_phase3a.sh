#!/usr/bin/env bash

set -u

TIMEOUT=120
UNWIND=12

rm -rf phase3a_results
mkdir -p phase3a_results

SUMMARY="phase3a_results/summary.tsv"

printf "case\tgood\tmutant\tgood_rc\tbad_rc\tgood_sec\tbad_sec\tgoto_lines\tunsupported_hits\n" \
    > "$SUMMARY"


get_verdict()
{
    FILE="$1"
    RC="$2"

    if grep -q "TIMED_OUT_BY_RUNNER" "$FILE"; then
        echo "TIMEOUT"
        return
    fi

    # Important: unsupported library calls may also end in
    # VERIFICATION FAILED. Classify them separately first.
    if grep -qiE \
        "Undefined function|Unsupported function|not yet supported|is not supported|unsupported function" \
        "$FILE"; then
        echo "UNSUPPORTED"
        return
    fi

    if grep -qiE \
        "Aborted|core dumped|Segmentation fault|uncaught exception|^ERROR:" \
        "$FILE"; then
        echo "ERROR"
        return
    fi

    if grep -q "VERIFICATION SUCCESSFUL" "$FILE"; then
        echo "SUCCESS"
        return
    fi

    if grep -q "VERIFICATION FAILED" "$FILE"; then
        echo "FAILED"
        return
    fi

    if [ "$RC" -ne 0 ]; then
        echo "PROCESS_ERROR"
        return
    fi

    echo "UNKNOWN"
}


run_one()
{
    SRC="$1"
    OUT="$2"
    RCFILE="$3"
    TIMEFILE="$4"

    DIR=$(dirname "$SRC")
    FILE=$(basename "$SRC")

    START=$(date +%s)

    (
        cd "$DIR"

        timeout "${TIMEOUT}s" \
            esbmc "$FILE" \
            --unwind "$UNWIND"
    ) > "$OUT" 2>&1

    RC=$?

    END=$(date +%s)
    SECS=$((END - START))

    echo "$RC" > "$RCFILE"
    echo "$SECS" > "$TIMEFILE"

    {
        echo
        echo "RUNNER_EXIT_CODE=$RC"
        echo "RUNNER_ELAPSED_SECONDS=$SECS"
    } >> "$OUT"

    if [ "$RC" -eq 124 ]; then
        echo "TIMED_OUT_BY_RUNNER" >> "$OUT"
    fi
}


dump_goto()
{
    SRC="$1"
    OUT="$2"

    DIR=$(dirname "$SRC")
    FILE=$(basename "$SRC")

    (
        cd "$DIR"

        timeout "${TIMEOUT}s" \
            esbmc \
            --goto-functions-only \
            "$FILE"
    ) > "$OUT" 2>&1 || true
}


for D in phase3a_cases/*
do
    CASE=$(basename "$D")
    R="phase3a_results/$CASE"

    mkdir -p "$R"

    echo
    echo "============================================================"
    echo "CASE: $CASE"
    echo "============================================================"

    echo "Running GOOD..."
    run_one \
        "$D/good.py" \
        "$R/good.txt" \
        "$R/good.rc" \
        "$R/good.time"

    echo "Running MUTANT..."
    run_one \
        "$D/bad.py" \
        "$R/bad.txt" \
        "$R/bad.rc" \
        "$R/bad.time"

    GRC=$(cat "$R/good.rc")
    BRC=$(cat "$R/bad.rc")

    GT=$(cat "$R/good.time")
    BT=$(cat "$R/bad.time")

    GV=$(get_verdict "$R/good.txt" "$GRC")
    BV=$(get_verdict "$R/bad.txt" "$BRC")

    echo "GOOD=$GV  MUTANT=$BV"

    dump_goto \
        "$D/good.py" \
        "$R/good.goto.txt"

    GLINES=$(wc -l < "$R/good.goto.txt")

    UHITS=$(
        grep -ciE \
            "Undefined function|Unsupported function|not yet supported|is not supported|unsupported function" \
            "$R/good.txt" \
            || true
    )

    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$CASE" \
        "$GV" \
        "$BV" \
        "$GRC" \
        "$BRC" \
        "$GT" \
        "$BT" \
        "$GLINES" \
        "$UHITS" \
        >> "$SUMMARY"
done


echo
echo
echo "============================================================"
echo " PHASE 3A LIBRARY FRONTIER SUMMARY"
echo "============================================================"

column -t -s $'\t' "$SUMMARY" 2>/dev/null || cat "$SUMMARY"


echo
echo
echo "============================================================"
echo " FRONTIER DIAGNOSTICS"
echo "============================================================"

for D in phase3a_cases/*
do
    CASE=$(basename "$D")
    R="phase3a_results/$CASE"

    GRC=$(cat "$R/good.rc")
    BRC=$(cat "$R/bad.rc")

    GV=$(get_verdict "$R/good.txt" "$GRC")
    BV=$(get_verdict "$R/bad.txt" "$BRC")

    # Healthy pair is SUCCESS / FAILED.
    if [ "$GV" != "SUCCESS" ] || [ "$BV" != "FAILED" ]; then

        echo
        echo "############################################################"
        echo "$CASE"
        echo "GOOD=$GV  MUTANT=$BV"
        echo "############################################################"

        echo
        echo "--- GOOD ---"
        grep -iE \
            "WARNING|ERROR|Undefined|Unsupported|not supported|VERIFICATION|exception|import|module" \
            "$R/good.txt" \
            | tail -n 80 \
            || true

        echo
        echo "--- MUTANT ---"
        grep -iE \
            "WARNING|ERROR|Undefined|Unsupported|not supported|VERIFICATION|exception|import|module" \
            "$R/bad.txt" \
            | tail -n 80 \
            || true
    fi
done
