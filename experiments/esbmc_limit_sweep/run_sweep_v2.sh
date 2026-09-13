#!/usr/bin/env bash

set -u

TIMEOUT=120
UNWIND=8

rm -rf results_v2
mkdir -p results_v2

SUMMARY="results_v2/summary.tsv"

printf "case\tpy_good\tpy_mutant\tc_good\tc_mutant\tpy_good_rc\tpy_bad_rc\tc_good_rc\tc_bad_rc\tpy_f_goto_lines\tc_f_goto_lines\n" \
    > "$SUMMARY"


###############################################################################
# Verdict classifier
###############################################################################

get_verdict()
{
    FILE="$1"
    RC="$2"

    if grep -q "VERIFICATION SUCCESSFUL" "$FILE"; then
        echo "SUCCESS"
        return
    fi

    if grep -q "VERIFICATION FAILED" "$FILE"; then
        echo "FAILED"
        return
    fi

    if grep -q "TIMED_OUT_BY_RUNNER" "$FILE"; then
        echo "TIMEOUT"
        return
    fi

    if grep -qiE \
        "Aborted|core dumped|uncaught exception|ERROR:|Segmentation fault|Assertion.*failed" \
        "$FILE"; then
        echo "ERROR"
        return
    fi

    if [ "$RC" -ne 0 ]; then
        echo "PROCESS_ERROR"
        return
    fi

    echo "UNKNOWN"
}


###############################################################################
# Run ESBMC
###############################################################################

run_esbmc()
{
    SRC="$1"
    OUT="$2"
    RCFILE="$3"

    echo
    echo "Running verification: $SRC"

    START=$(date +%s)

    timeout "${TIMEOUT}s" \
        esbmc \
        "$SRC" \
        --unwind "$UNWIND" \
        > "$OUT" 2>&1

    RC=$?

    END=$(date +%s)
    ELAPSED=$((END - START))

    echo "$RC" > "$RCFILE"

    {
        echo
        echo "RUNNER_EXIT_CODE=$RC"
        echo "RUNNER_ELAPSED_SECONDS=$ELAPSED"
    } >> "$OUT"

    if [ "$RC" -eq 124 ]; then
        echo "TIMED_OUT_BY_RUNNER" >> "$OUT"
    fi
}


###############################################################################
# GOTO helpers
###############################################################################

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


###############################################################################
# Run all cases
###############################################################################

for CASEDIR in cases/*
do
    CASE=$(basename "$CASEDIR")

    echo
    echo "============================================================"
    echo "CASE: $CASE"
    echo "============================================================"

    RDIR="results_v2/$CASE"
    mkdir -p "$RDIR"


    run_esbmc \
        "$CASEDIR/good.py" \
        "$RDIR/python_good.txt" \
        "$RDIR/python_good.rc"

    run_esbmc \
        "$CASEDIR/bad.py" \
        "$RDIR/python_bad.txt" \
        "$RDIR/python_bad.rc"

    run_esbmc \
        "$CASEDIR/good.c" \
        "$RDIR/c_good.txt" \
        "$RDIR/c_good.rc"

    run_esbmc \
        "$CASEDIR/bad.c" \
        "$RDIR/c_bad.txt" \
        "$RDIR/c_bad.rc"


    PYGOOD_RC=$(cat "$RDIR/python_good.rc")
    PYBAD_RC=$(cat "$RDIR/python_bad.rc")
    CGOOD_RC=$(cat "$RDIR/c_good.rc")
    CBAD_RC=$(cat "$RDIR/c_bad.rc")


    PYGOOD=$(get_verdict "$RDIR/python_good.txt" "$PYGOOD_RC")
    PYBAD=$(get_verdict "$RDIR/python_bad.txt" "$PYBAD_RC")
    CGOOD=$(get_verdict "$RDIR/c_good.txt" "$CGOOD_RC")
    CBAD=$(get_verdict "$RDIR/c_bad.txt" "$CBAD_RC")


    dump_goto \
        "$CASEDIR/good.py" \
        "$RDIR/python.goto.txt"

    dump_goto \
        "$CASEDIR/good.c" \
        "$RDIR/c.goto.txt"


    extract_py_f \
        "$RDIR/python.goto.txt" \
        "$RDIR/python_f.goto"

    extract_c_f \
        "$RDIR/c.goto.txt" \
        "$RDIR/c_f.goto"


    PYLINES=$(wc -l < "$RDIR/python_f.goto")
    CLINES=$(wc -l < "$RDIR/c_f.goto")


    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$CASE" \
        "$PYGOOD" \
        "$PYBAD" \
        "$CGOOD" \
        "$CBAD" \
        "$PYGOOD_RC" \
        "$PYBAD_RC" \
        "$CGOOD_RC" \
        "$CBAD_RC" \
        "$PYLINES" \
        "$CLINES" \
        >> "$SUMMARY"
done


###############################################################################
# Print summary
###############################################################################

echo
echo
echo "============================================================"
echo " CAPABILITY SWEEP V2 SUMMARY"
echo "============================================================"
echo

column -t -s $'\t' "$SUMMARY" 2>/dev/null || cat "$SUMMARY"


###############################################################################
# Print concise diagnostics for every non-standard verdict
###############################################################################

echo
echo
echo "============================================================"
echo " NON-STANDARD VERDICT DIAGNOSTICS"
echo "============================================================"

for CASEDIR in cases/*
do
    CASE=$(basename "$CASEDIR")
    RDIR="results_v2/$CASE"

    for NAME in python_good python_bad c_good c_bad
    do
        RC=$(cat "$RDIR/$NAME.rc")
        VERDICT=$(get_verdict "$RDIR/$NAME.txt" "$RC")

        if [ "$VERDICT" != "SUCCESS" ] && [ "$VERDICT" != "FAILED" ]; then
            echo
            echo "------------------------------------------------------------"
            echo "$CASE / $NAME"
            echo "VERDICT=$VERDICT RC=$RC"
            echo "------------------------------------------------------------"

            tail -n 40 "$RDIR/$NAME.txt"
        fi
    done
done


echo
echo
echo "============================================================"
echo " INTERPRETATION"
echo "============================================================"

echo "SUCCESS / FAILED means ESBMC produced an actual verification verdict."
echo
echo "Expected healthy mutation test:"
echo "  good   = SUCCESS"
echo "  mutant = FAILED"
echo
echo "Suspicious:"
echo "  good SUCCESS + mutant SUCCESS"
echo "    -> possible vacuous/unsound modelling"
echo
echo "Unsupported/problem:"
echo "  good ERROR or PROCESS_ERROR"
echo
echo "Scalability:"
echo "  TIMEOUT"
echo
echo "Detailed outputs:"
echo "  results_v2/"
