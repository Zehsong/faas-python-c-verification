"""Case-independent predicate discovery and final certification driver."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import time
from c_backend import save_json
from predicate_search import search
from result_contract import ExecutionFailure, build_summary, write_summary

def run(args, backend_type):
    started = time.monotonic()
    root = Path(args.workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix=args.variant + "-", dir=root))
    report = {"status": "UNKNOWN", "variant": args.variant, "state_mode": args.state_mode,
              "created_utc": datetime.now(timezone.utc).isoformat(), "artifacts": str(workdir),
              "condition": None, "exact": False, "uses_llm_api": False,
              "method": "trace-guided finite predicate partition with ESBMC certification"}
    backend = None
    try:
        atoms = backend_type.initial_atoms()
        extra_seeds = []
        if args.hypotheses:
            proposal = json.loads(Path(args.hypotheses).read_text(encoding="utf-8"))
            if not isinstance(proposal, dict) or set(proposal) - {"predicates", "seeds"}:
                raise ValueError("hypotheses only accept predicates and seeds; no claimed verdicts")
            if not isinstance(proposal.get("predicates", []), list) or not isinstance(proposal.get("seeds", []), list):
                raise ValueError("predicates and seeds must be arrays")
            if len(proposal.get("seeds", [])) > 256:
                raise ValueError("at most 256 proposed seeds are supported")
            for text in proposal.get("predicates", []):
                atom = backend_type.atom_type.parse(text)
                if atom not in atoms:
                    atoms.append(atom)
            extra_seeds = [backend_type.validate_seed(row) for row in proposal.get("seeds", [])]
            save_json(workdir / "hypotheses.json", proposal)
        if len(atoms) > args.max_predicates:
            raise ValueError("initial vocabulary exceeds --max-predicates")
        backend = backend_type(args, workdir)
        report["scope"] = backend.scope
        report["sketch"] = backend.sketch_manifest
        backend.prepare()
        obligations = backend.state_obligations() if backend.proof_before_replay else None
        if obligations is not None:
            report["state_obligations"] = obligations
            if any(result["status"] != "PROVED" for result in obligations.values()):
                code = "STATE_OBLIGATION_NOT_PROVED" if "initialization" in obligations else "SAFETY_NOT_ESTABLISHED"
                raise ExecutionFailure(code, "required state/safety obligations not established; native replay disabled")
        backend.replay(backend.default_seeds(args.state_mode))
        backend.replay(extra_seeds, origin="untrusted_hypotheses")
        if obligations is None:
            obligations = backend.state_obligations()
        report["state_obligations"] = obligations
        if any(result["status"] != "PROVED" for result in obligations.values()):
            raise RuntimeError("initialization/invariant preservation not established; no certified condition")
        found = search(backend, atoms, args.max_predicates)
        report["search"] = found
        if found.get("history") and found["history"][0].get("cube") in ([], ()) and found["history"][0]["status"] == "EMPTY":
            report["domain_feasibility"] = found["history"][0]["evidence"]
            if backend.samples:
                raise ExecutionFailure("WITNESS_MISMATCH", "solver/native domain-feasibility disagreement")
            raise ExecutionFailure("EMPTY_DOMAIN", "declared domain proved unreachable; no equivalence claim")
        presentation = backend.present_condition(found)
        report["condition"] = presentation["condition"]
        # Revalidate the published condition; prove its complement contains only
        # unequal observations before claiming an exact domain within this model.
        final = backend.query("equal", presentation["condition_c"])
        outside = backend.query("different", f"!({presentation['condition_c']})")
        report["final_validation"] = {"sufficiency": final, "complement": outside}
        report["exact"] = final["status"] == "PROVED" and outside["status"] == "PROVED"
        report["status"] = "EXACT" if report["exact"] else "PARTIAL" if found["buckets"]["EQ"] else "UNKNOWN"
        report["condition_c"] = presentation["condition_c"]
        report["condition_basis"] = presentation["basis"]
        report["published_sufficiency"] = final
        report["published_complement"] = outside
        if final["status"] == "UNKNOWN" and found["buckets"]["EQ"]:
            regions = [event["evidence"] for event in found.get("history", []) if event["status"] == "EQ"]
            if len(regions) == len(found["buckets"]["EQ"]) and all(q["status"] == "PROVED" for q in regions):
                # Keep only the union actually certified during search. A compact
                # presentation whose final check timed out must not be promoted.
                report.update(condition=found["condition"], condition_c=found["condition_c"],
                              condition_basis="Boolean union of individually proved nonempty regions",
                              published_sufficiency={"status": "PROVED", "basis": "PROVED_REGION_UNION", "regions": regions})
                if presentation["condition_c"] != found["condition_c"]:
                    report["published_complement"] = {"status": "NOT_CHECKED", "basis": "condition reverted to certified region union",
                                                      "prior_presentation_check": outside}
            else:
                report.update(status="UNKNOWN", condition=None, condition_c=None)
        if final["status"] == "REFUTED" or (final["status"] == "UNKNOWN" and (
                final.get("reason", "").startswith("solver/native") or final.get("reason_code") == "WITNESS_REPLAY_FAILED")):
            report.update(status="UNKNOWN", exact=False, condition=None, condition_c=None,
                          reason="final validation contradicted prior certificates; do not use this condition", reason_code="CERTIFICATE_CONTRADICTION")
        # Do not present an empty sufficient condition as a useful discovery.
        if not found["buckets"]["EQ"] and not report["exact"]:
            report["condition"] = None
    except (OSError, ValueError, RuntimeError) as exc:
        report["reason"] = str(exc)
        if getattr(exc, "code", None):
            report["reason_code"] = exc.code
        elif isinstance(exc, ValueError):
            report["reason_code"] = "INPUT_REJECTED"
        elif isinstance(exc, OSError):
            report["reason_code"] = "INPUT_OR_TOOL_IO_ERROR"
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    if backend:
        report.update(esbmc=backend.esbmc, esbmc_version_output=backend.version,
                      queries_used=len(backend.queries), traces_collected=len(backend.samples))
        save_json(workdir / "traces.json", backend.samples)
        save_json(workdir / "replays.json", backend.replays)
        save_json(workdir / "queries.json", backend.queries)
        save_json(workdir / "agent-context.json", {
            "scope": backend.scope, "model_source": backend.model,
            "variant_function": backend.variants[args.variant], "traces": backend.samples,
            "current_result": report, "proposal_schema": {"predicates": ["x == 42"], "seeds": []},
            "trust": "Propose only entry-state predicates or inputs; labels and proof claims are not accepted."})
    save_json(workdir / "result.json", report)
    save_json(root / "result.json", report)
    summary = build_summary(report, samples=backend.samples if backend else (), queries=backend.queries if backend else ())
    write_summary(workdir, summary)
    write_summary(root, summary)
    print(f"{report['status']}: {report['condition']}")
    print(f"Outcome: {summary['status']}; domain={summary['domain']['status']}; claim={summary['claim']['meaning']}")
    codes = list(dict.fromkeys(d["code"] for d in summary["diagnostics"]))
    if codes:
        print("Diagnostics: " + ", ".join(codes))
    print(f"Report: {workdir / 'report.md'}")
    print(f"Artifacts: {workdir}")
    return report
