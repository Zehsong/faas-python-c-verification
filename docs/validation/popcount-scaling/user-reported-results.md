# User-reported popcount scaling — 2026-09-16

Reported after implementation `ed1fe9b`:

```text
Artifacts: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-scaling-stage/run-K0LJAV/scaling-97kf3lz4/r2-b8/pair-rh137u1w
 query 000 expected: PROVED
r2-b8: EXACT; full-domain certified=True
POPCOUNT SCALING: RECORDED (10/10 valid runs; full-domain certified=8/10)
Open overview: /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-scaling-stage/run-K0LJAV/scaling-97kf3lz4/README.md
Evidence directory: /home/codespace/equiv-evidence/popcount-scaling-20260916T123626Z-qpnxZE
Downloadable archive: /home/codespace/equiv-evidence/popcount-scaling-20260916T123626Z-qpnxZE.tar.gz
```

The user reports valid measurement records for all ten scheduled runs and eight
full-domain certificates. The only individually identified outcome in this
excerpt is r2-b8: EXACT, with its post-discovery expected-condition query PROVED.

The remaining width/repetition outcomes, actual formulas, times, diagnostics,
post-checks and source/tool identities have not been independently inspected.
In particular, **do not assume that the two uncertified runs are both 32-bit
timeouts**. An uncertified row can have a non-EXACT discovery result or an
unproved full-domain post-check. The earlier 32-bit UNKNOWN belongs to the
separate external-integration experiment and does not identify these two rows.

This is eight certificates across ten repeated measurements of one function
pair, not an 80% success rate on ten independent programs. Two repetitions do
not establish a stable timing estimate, a sharp width threshold or general C
scalability. Preserve the source protocol and original budgets while reviewing
the details. No new solver execution is needed to retrieve them:

```bash
cat /workspaces/faas-python-c-verification/.verify-equiv-runs/popcount-scaling-stage/run-K0LJAV/scaling-97kf3lz4/metrics.csv
```

The CSV includes each run's width, discovery status, condition, certificate and
measurement flags, query/time metrics, timeout kinds and diagnostic codes.
If an EXACT row lacks a full-domain certificate, inspect its `full_domain_check`
in the existing `results.json` before classifying the reason. The raw archive
and checksum sidecar remain in the user's Codespace; they were not opened here.

[Protocol](../../../cases/c_external_bits/SCALING.md) · [Local controls](README.md)
