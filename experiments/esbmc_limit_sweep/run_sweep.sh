#!/usr/bin/env bash

set -u

TIMEOUT=120
UNWIND=8

mkdir -p results

SUMMARY="results/summary.tsv"

printf "case\tpy_good\tpy_mutant\tc_good\tc_mutant\tpy_f_goto_lines\tc_f_goto_lines\n" \
    > "$SUMMARY"


get_verdict()
{
    FILE="$1"

    if grep -q "VERIFICATION SUCCESSFUL" "$FILE"; then
        echo "SUCCESS"
    elif grep -q "VERIFICATION FAILED" "$FILE"; then
        echo "FAILED"
    elif grep -qi "timed out" "$FILE"; then
        echo "TIMEOUT"
    elif grep -qiE "Aborted|core dumped|uncaught exception|ERROR:" "$FILE"; then
        echo "ERROR"
    else
        echo "UNKNOWN"
    fi
}


run_esbmc()
{
    SRC="$1"
    OUT="$2"

    echo "Running $SRC"

    timeout "${TIMEOUT}s" \
        /usr/bin/time \
        -f "RESOURCE wall=%e maxrss=%MKB" \
        esbmc "$SRC" \
        --unwind "$UNWIND" \
        > "$OUT" 2>&1

    RC=$?

    if [ "$RC" -eq 124 ]; then
        echo "TIMED OUT" >> "$OUT"
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


extract_py_f()
{
    IN="$1"
    OUT="$2"

    awk '
    /^f \(py:.*@F@f\):/ { inside=1 }
    inside { print }
    inside && /^\^+$/ { exit }
    ' "$IN" > "$OUT"
}


extract_c_f()
{
    IN="$1"
    OUT="$2"

    awk '
    /^f \(c:@F@f\):/ { inside=1 }
    inside { print }
    inside && /^\^+$/ { exit }
    ' "$IN" > "$OUT"
}


for CASEDIR in cases/*
do
    CASE=$(basename "$CASEDIR")

    echo
    echo "============================================================"
    echo "CASE: $CASE"
    echo "============================================================"

    mkdir -p "results/$CASE"

    run_esbmc \
        "$CASEDIR/good.py" \
        "results/$CASE/python_good.txt"

    run_esbmc \
        "$CASEDIR/bad.py" \
        "results/$CASE/python_bad.txt"

    run_esbmc \
        "$CASEDIR/good.c" \
        "results/$CASE/c_good.txt"

    run_esbmc \
        "$CASEDIR/bad.c" \
        "results/$CASE/c_bad.txt"


    PYGOOD=$(get_verdict "results/$CASE/python_good.txt")
    PYBAD=$(get_verdict "results/$CASE/python_bad.txt")
    CGOOD=$(get_verdict "results/$CASE/c_good.txt")
    CBAD=$(get_verdict "results/$CASE/c_bad.txt")


    dump_goto \
        "$CASEDIR/good.py" \
        "results/$CASE/python.goto.txt"

    dump_goto \
        "$CASEDIR/good.c" \
        "results/$CASE/c.goto.txt"


    extract_py_f \
        "results/$CASE/python.goto.txt" \
        "results/$CASE/python_f.goto"

    extract_c_f \
        "results/$CASE/c.goto.txt" \
        "results/$CASE/c_f.goto"


    PYLINES=$(wc -l < "results/$CASE/python_f.goto")
    CLINES=$(wc -l < "results/$CASE/c_f.goto")


    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$CASE" \
        "$PYGOOD" \
        "$PYBAD" \
        "$CGOOD" \
        "$CBAD" \
        "$PYLINES" \
        "$CLINES" \
        >> "$SUMMARY"
done


echo
echo "============================================================"
echo " CAPABILITY SWEEP SUMMARY"
echo "============================================================"
echo

column -t -s $'\t' "$SUMMARY" 2>/dev/null || cat "$SUMMARY"

echo
echo "Interpretation:"
echo "  good SUCCESS + mutant FAILED = GREEN"
echo "  good not SUCCESS             = unsupported/frontend/model problem"
echo "  good SUCCESS + mutant SUCCESS = UNSOUND/VACUOUS SUSPECT"
echo "  timeout                      = scalability limit"
echo
echo "Detailed logs are under results/"
