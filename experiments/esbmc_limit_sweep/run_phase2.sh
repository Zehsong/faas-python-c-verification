#!/usr/bin/env bash

set -u

TIMEOUT=120
UNWIND=10

rm -rf phase2_results
mkdir -p phase2_results

SUMMARY="phase2_results/summary.tsv"

printf "case\tpy_good\tpy_mutant\tc_good\tc_mutant\tpy_rc_good\tpy_rc_bad\tc_rc_good\tc_rc_bad\tpy_goto\tc_goto\n" \
    > "$SUMMARY"


get_verdict()
{
    FILE="$1"
    RC="$2"

    if grep -q "VERIFICATION SUCCESSFUL" "$FILE"; then
        echo "SUCCESS"
    elif grep -q "VERIFICATION FAILED" "$FILE"; then
        echo "FAILED"
    elif grep -q "TIMED_OUT_BY_RUNNER" "$FILE"; then
        echo "TIMEOUT"
    elif grep -qiE \
        "Aborted|core dumped|uncaught exception|ERROR:|Segmentation fault|Assertion.*failed" \
        "$FILE"; then
        echo "ERROR"
    elif [ "$RC" -ne 0 ]; then
        echo "PROCESS_ERROR"
    else
        echo "UNKNOWN"
    fi
}


run_one()
{
    SRC="$1"
    OUT="$2"
    RCFILE="$3"

    timeout "${TIMEOUT}s" \
        esbmc "$SRC" \
        --unwind "$UNWIND" \
        > "$OUT" 2>&1

    RC=$?

    echo "$RC" > "$RCFILE"

    if [ "$RC" -eq 124 ]; then
        echo "TIMED_OUT_BY_RUNNER" >> "$OUT"
    fi
}


dump_goto()
{
    SRC="$1"
    OUT="$2"

    timeout "${TIMEOUT}s" \
        esbmc \
        --goto-functions-only \
        "$SRC" \
        > "$OUT" 2>&1 || true
}


for D in phase2_cases/*
do
    CASE=$(basename "$D")
    R="phase2_results/$CASE"

    mkdir -p "$R"

    echo
    echo "============================================================"
    echo "$CASE"
    echo "============================================================"

    run_one "$D/good.py" "$R/py_good.txt" "$R/py_good.rc"
    run_one "$D/bad.py"  "$R/py_bad.txt"  "$R/py_bad.rc"
    run_one "$D/good.c"  "$R/c_good.txt"  "$R/c_good.rc"
    run_one "$D/bad.c"   "$R/c_bad.txt"   "$R/c_bad.rc"

    PYGR=$(cat "$R/py_good.rc")
    PYBR=$(cat "$R/py_bad.rc")
    CGR=$(cat "$R/c_good.rc")
    CBR=$(cat "$R/c_bad.rc")

    PYG=$(get_verdict "$R/py_good.txt" "$PYGR")
    PYB=$(get_verdict "$R/py_bad.txt" "$PYBR")
    CG=$(get_verdict "$R/c_good.txt" "$CGR")
    CB=$(get_verdict "$R/c_bad.txt" "$CBR")

    dump_goto "$D/good.py" "$R/py.goto.txt"
    dump_goto "$D/good.c" "$R/c.goto.txt"

    PYLINES=$(wc -l < "$R/py.goto.txt")
    CLINES=$(wc -l < "$R/c.goto.txt")

    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$CASE" \
        "$PYG" "$PYB" "$CG" "$CB" \
        "$PYGR" "$PYBR" "$CGR" "$CBR" \
        "$PYLINES" "$CLINES" \
        >> "$SUMMARY"
done


echo
echo
echo "============================================================"
echo " PHASE 2 SUMMARY"
echo "============================================================"

column -t -s $'\t' "$SUMMARY" 2>/dev/null || cat "$SUMMARY"


echo
echo
echo "============================================================"
echo " NON-STANDARD DIAGNOSTICS"
echo "============================================================"

for D in phase2_cases/*
do
    CASE=$(basename "$D")
    R="phase2_results/$CASE"

    for X in py_good py_bad c_good c_bad
    do
        RC=$(cat "$R/$X.rc")
        V=$(get_verdict "$R/$X.txt" "$RC")

        if [ "$V" != "SUCCESS" ] && [ "$V" != "FAILED" ]; then
            echo
            echo "----- $CASE / $X : $V (rc=$RC) -----"
            tail -n 50 "$R/$X.txt"
        fi
    done
done
