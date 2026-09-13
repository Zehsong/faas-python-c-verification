"""Run one named C assertion using the existing oracle's fail-closed parser.

PROVED/REFUTED refer to the requested assertion, not necessarily equivalence.
The caller owns reachability, source modelling and the meaning of the property.
"""


def check(oracle, command, logfile, timeout, property_name):
    rc, timed_out = oracle.run(command, logfile, timeout)
    verdict = oracle.classify_verification(logfile, property_name)
    status = "UNKNOWN"
    if not timed_out and verdict == "EQ" and rc == 0:
        status = "PROVED"
    elif not timed_out and verdict == "NEQ" and rc != 0:
        status = "REFUTED"
    return {"status": status, "returncode": rc, "timed_out": timed_out,
            "property": property_name, "command": [str(x) for x in command],
            "log": str(logfile), "violation": oracle.extract_violated_property(logfile)}
