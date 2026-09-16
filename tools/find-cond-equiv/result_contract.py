"""Versioned, conservative proof summaries shared by discovery and sessions.

Legacy result.json remains available. These summaries explain existing evidence;
they do not invoke a solver or promote samples into universal certificates.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile


class InputFailure(ValueError):
    def __init__(self, code, message, scope=None):
        super().__init__(message)
        self.code, self.scope = code, scope


class ExecutionFailure(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def diagnostic_code(record):
    if record.get("reason_code"):
        return record["reason_code"]
    if record.get("timed_out"):
        return "SOLVER_TIMEOUT"
    violation = str(record.get("violation") or "").lower()
    if "unwinding assertion" in violation:
        return "UNWINDING_INCOMPLETE"
    if violation and record.get("status") == "UNKNOWN":
        return "SAFETY_OR_OTHER_PROPERTY_FAILURE"
    text = str(record.get("reason") or "").lower()
    # Fallback for older evidence and adapter-specific diagnostic strings.
    for needle, code in (("identity changed", "IDENTITY_CHANGED"), ("source or tool", "IDENTITY_CHANGED"),
                         ("source, contract", "IDENTITY_CHANGED"), ("solver/native", "WITNESS_MISMATCH"),
                         ("native replay did not reach", "WITNESS_MISMATCH"),
                         ("predicate vocabulary", "VOCABULARY_EXHAUSTED"),
                         ("initial vocabulary", "VOCABULARY_LIMIT"),
                         ("budget exhausted", "BUDGET_EXHAUSTED"),
                         ("esbmc unavailable", "SOLVER_UNAVAILABLE"),
                         ("native counterexample", "CANDIDATE_REFUTED"),
                         ("native replay disabled", "SAFETY_NOT_ESTABLISHED"),
                         ("native replay", "NATIVE_REPLAY_FAILED")):
        if needle in text:
            return code
    return "PROPERTY_REFUTED" if record.get("status") == "REFUTED" else "NOT_ESTABLISHED"


def evidence(record=None, default="NOT_CHECKED"):
    record = record or {}
    return {"status": record.get("status", default), "basis": record.get("basis", "solver" if record else None),
            "log": record.get("log"), "property": record.get("property"),
            "reason_code": diagnostic_code(record) if record.get("status") == "UNKNOWN" else record.get("reason_code"),
            "details": record}


def collect_diagnostics(value, path="result"):
    result, seen = [], set()
    def visit(node, location):
        if isinstance(node, dict):
            leaf_unknown = node.get("status") == "UNKNOWN" and not any(
                name in node for name in ("state_obligations", "search", "evidence", "property_result", "checks"))
            if node.get("reason") or node.get("reason_code") or leaf_unknown:
                code = diagnostic_code(node)
                message = node.get("reason") or node.get("violation") or "This check did not establish a result."
                key = (code, str(message), node.get("log"))
                if key not in seen:
                    seen.add(key)
                    result.append({"code": code, "message": str(message), "location": location, "log": node.get("log")})
            for key, child in node.items():
                if key not in ("scope", "model_source", "samples", "traces", "sketch", "identity"):
                    visit(child, location + "." + str(key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{location}[{index}]")
    visit(value, path)
    return result


def _domain(report, samples, queries):
    if report.get("reason_code") == "EMPTY_DOMAIN" or report.get("phase") == "EMPTY_DOMAIN":
        return {"status": "EMPTY", "basis": report.get("domain_basis", "feasibility proof"),
                "evidence": report.get("domain_feasibility")}
    query = report.get("domain_feasibility")
    if query and query.get("status") == "REFUTED":
        return {"status": "NONEMPTY", "basis": "refuted false assertion", "evidence": query}
    if query and query.get("status") == "PROVED" and not samples:
        return {"status": "EMPTY", "basis": "proved false assertion unreachable", "evidence": query}
    if samples:
        return {"status": "NONEMPTY", "basis": "validated native input", "evidence": samples[0]}
    witness = next((q for q in queries if q.get("kind") == "feasible" and q.get("status") == "REFUTED"), None)
    return {"status": "NONEMPTY" if witness else "NOT_ESTABLISHED",
            "basis": "refuted false assertion" if witness else None, "evidence": witness}


def build_summary(report, *, producer="finder", samples=(), queries=(), state=None):
    source = state if state is not None else report
    best = (state.get("best_result") or {}) if state is not None else report
    checks = best.get("checks", {}) if state is not None else report.get("final_validation", {})
    suff = checks.get("sufficiency") if state is not None else report.get("published_sufficiency", checks.get("sufficiency"))
    complement = checks.get("complement") if state is not None else report.get("published_complement", checks.get("complement"))
    condition = best.get("candidate") if state is not None else report.get("condition")
    condition_c = best.get("candidate_c") if state is not None else report.get("condition_c")
    obligations = source.get("state_obligations", {})
    required = (source.get("scope") or {}).get("required_state_obligations", [])
    obligations = {**{name: {"status": "NOT_CHECKED", "reason_code": "STATE_OBLIGATION_MISSING",
                            "reason": "Required state obligation missing: " + name}
                     for name in required}, **obligations}
    domain = _domain(source, samples, queries)
    diagnostics = collect_diagnostics(source)
    diagnostics += collect_diagnostics({name: q for name, q in obligations.items() if name not in source.get("state_obligations", {})}, "obligations.state")
    # Empty domains and stale evidence cannot be published as equivalence claims.
    admitted = bool(source.get("scope")) and all(q.get("status") == "PROVED" for q in obligations.values())
    stale = source.get("phase") == "BLOCKED" or source.get("reason_code") in ("IDENTITY_CHANGED", "CERTIFICATE_CONTRADICTION")
    status = "UNKNOWN"
    if domain["status"] == "EMPTY":
        status = "EMPTY_DOMAIN"
    elif admitted and not stale and domain["status"] == "NONEMPTY" and condition is not None and suff and suff.get("status") == "PROVED":
        if report.get("status") == "EXACT" and complement and complement.get("status") == "PROVED":
            status = "EXACT"
        elif report.get("status") in ("EXACT", "PARTIAL") and condition != "false":
            status = "PARTIAL"
    if status not in ("EXACT", "PARTIAL"):
        condition = condition_c = None
    if status == "EMPTY_DOMAIN" and not any(d["code"] == "EMPTY_DOMAIN" for d in diagnostics):
        diagnostics.append({"code": "EMPTY_DOMAIN", "message": "No admissible input exists; no equivalence claim is published.",
                            "location": "domain", "log": (source.get("domain_feasibility") or {}).get("log")})
    meaning = ("ALL_INPUTS" if condition == "true" else "NO_INPUTS" if condition == "false" else "REGION") if status == "EXACT" else (
        "SUFFICIENT_REGION" if status == "PARTIAL" else "NO_EQUIVALENCE_CLAIM")
    if status == "PARTIAL" and not any(d["code"] == "COMPLETENESS_NOT_ESTABLISHED" for d in diagnostics):
        diagnostics.append({"code": "COMPLETENESS_NOT_ESTABLISHED", "message": "Equality is certified inside this condition; inputs outside it are not all certified unequal.",
                            "location": "obligations.complement", "log": (complement or {}).get("log")})
    if status == "UNKNOWN" and not diagnostics:
        diagnostics.append({"code": "AWAITING_PROPOSAL" if source.get("phase") == "READY" else "NOT_ESTABLISHED",
                            "message": "No certified condition has been established.", "location": "result", "log": None})
    if stale:
        domain = {"status": "NOT_ESTABLISHED", "basis": "previous evidence invalidated by identity drift or contradiction", "evidence": None}
        obligations = {name: {"status": "INVALIDATED", "basis": "source identity or evidence contradiction", "previous": q}
                       for name, q in obligations.items()}
        suff = {"status": "INVALIDATED", "basis": "source identity or evidence contradiction", "previous": suff}
        complement = {"status": "INVALIDATED", "basis": "source identity or evidence contradiction", "previous": complement}
    latest = source.get("latest_feedback") if state is not None else None
    return {"schema": "conditional-equivalence-result", "schema_version": 1, "producer": producer,
            "status": status, "legacy_status": report.get("status"), "scope": source.get("scope"),
            "claim": {"meaning": meaning, "condition": condition, "condition_c": condition_c,
                      "relative_to_declared_scope": True},
            "domain": domain,
            "obligations": {"state": {name: evidence(q) for name, q in obligations.items()},
                            "sufficiency": evidence(suff), "complement": evidence(complement)},
            "diagnostics": diagnostics, "latest_candidate": latest,
            "metrics": {"queries": report.get("queries_used", 0), "native_samples": len(samples),
                        "elapsed_seconds": report.get("elapsed_seconds", report.get("active_seconds"))},
            "artifacts": {"directory": report.get("artifacts"), "legacy_result": "result.json",
                          "summary": "verification-result.json", "human_report": "report.md"}}


def render(summary):
    claim = summary["claim"]
    meanings = {"ALL_INPUTS": "The programs agree on every admissible input.",
                "NO_INPUTS": "The domain is nonempty, and the programs differ on every admissible input.",
                "REGION": "This condition describes exactly which admissible inputs produce equal observations.",
                "SUFFICIENT_REGION": "Equality is proved inside this condition; its complement is not completely classified.",
                "NO_EQUIVALENCE_CLAIM": "No certified equivalence condition is published."}
    lines = ["# Conditional equivalence result", "", f"Status: **{summary['status']}**", "",
             f"Meaning: {claim['meaning']}. Domain: {summary['domain']['status']}.", "",
             meanings[claim["meaning"]], "",
             "All claims are relative to the declared inputs, observations and verification bounds.", ""]
    if claim["condition"] is not None:
        lines += ["## Certified condition", "", "```text", claim["condition"], "```", ""]
    lines += ["## Scope", "", "```json", json.dumps(summary["scope"], indent=2, ensure_ascii=False), "```", "",
              "## Proof obligations", "", "| Check | Status | Basis |", "|---|---|---|"]
    checks = {**summary["obligations"]["state"], **{k: summary["obligations"][k] for k in ("sufficiency", "complement")}}
    for name, record in checks.items():
        lines.append(f"| {name} | {record['status']} | {record['basis'] or 'not run'} |")
    lines += ["", "## Diagnostics", ""]
    for item in summary["diagnostics"]:
        lines.append(f"- **{item['code']}**: {item['message']}")
        if item["log"]:
            lines.append(f"  Evidence: `{item['log']}`")
    if not summary["diagnostics"]:
        lines.append("No unresolved diagnostic was recorded.")
    lines += ["", "## Cost and artifacts", "", f"Queries: {summary['metrics']['queries']}; native samples: {summary['metrics']['native_samples']}.",
              f"Elapsed/active seconds: {summary['metrics']['elapsed_seconds']}.", "",
              "`verification-result.json` contains structured checks and evidence references; `result.json` retains the legacy output.", ""]
    return "\n".join(lines)


def write_summary(directory, summary):
    validate_summary(summary)
    directory = Path(directory)
    # Single-writer session lock or per-run directory owns these files.
    for name, content in (("verification-result.json", json.dumps(summary, indent=2, ensure_ascii=False) + "\n"),
                          ("report.md", render(summary))):
        temporary = directory / (name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(directory / name)


def validate_summary(summary):
    """Validate v1 invariants without adding a JSON-schema runtime dependency."""
    if summary.get("schema") != "conditional-equivalence-result" or type(summary.get("schema_version")) is not int or summary["schema_version"] != 1:
        raise ValueError("unsupported result schema")
    if summary.get("status") not in ("EXACT", "PARTIAL", "UNKNOWN", "EMPTY_DOMAIN"):
        raise ValueError("invalid summary status")
    if summary.get("producer") not in ("finder", "agent") or not isinstance(summary.get("diagnostics"), list):
        raise ValueError("invalid summary producer/diagnostics")
    claim, domain, checks = summary["claim"], summary["domain"], summary["obligations"]
    if claim.get("relative_to_declared_scope") is not True or domain["status"] not in ("NONEMPTY", "EMPTY", "NOT_ESTABLISHED"):
        raise ValueError("claim must be scope-restricted with an explicit domain status")
    if summary["status"] in ("EXACT", "PARTIAL"):
        if not all(isinstance(claim.get(k), str) for k in ("condition", "condition_c")) or not summary.get("scope"):
            raise ValueError("certified claims require condition and scope")
        if domain["status"] != "NONEMPTY" or checks["sufficiency"]["status"] != "PROVED" or any(
                q["status"] != "PROVED" for q in checks["state"].values()):
            raise ValueError("certified claim lacks domain/state/sufficiency evidence")
        if any(checks["state"].get(name, {}).get("status") != "PROVED"
               for name in summary["scope"].get("required_state_obligations", [])):
            raise ValueError("certified claim lacks a required state obligation")
        if summary["status"] == "EXACT" and checks["complement"]["status"] != "PROVED":
            raise ValueError("EXACT requires complementary inequality evidence")
    elif claim.get("condition") is not None or claim.get("condition_c") is not None:
        raise ValueError("uncertified result cannot publish a certified condition")
    if summary["status"] == "EMPTY_DOMAIN" and domain["status"] != "EMPTY":
        raise ValueError("empty domain must be explicit")
    return summary


def failure_result(args, exc, producer="finder"):
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="rejected-", dir=root))
    code = getattr(exc, "code", "INPUT_IO_ERROR" if isinstance(exc, OSError) else "INPUT_REJECTED")
    report = {"status": "UNKNOWN", "condition": None, "exact": False, "reason": str(exc), "reason_code": code,
              "scope": getattr(exc, "scope", None), "created_utc": datetime.now(timezone.utc).isoformat(),
              "artifacts": str(directory), "queries_used": 0, "traces_collected": 0,
              "request": {"contract": getattr(args, "contract", None), "variant": getattr(args, "variant", None)}}
    if code == "EMPTY_DOMAIN":
        report["domain_basis"] = "contradictory inclusive rectangular bounds; source admission not completed"
    summary = build_summary(report, producer=producer)
    for dest in (directory, root):
        (dest / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        write_summary(dest, summary)
    label = summary["status"] if code == summary["status"] else f"{summary['status']}: {code}"
    print(f"{label}: {exc}")
    print(f"Report: {directory / 'report.md'}")
    return report
