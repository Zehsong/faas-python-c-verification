#!/usr/bin/env python3
"""Persistent propose/check/feedback sessions using reviewed C case adapters.

The external agent reads agent-context.json and supplies proposal JSON. No model
API, shell command, arbitrary harness or claimed verdict is accepted as a proposal.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import time
import uuid

from agent_conditions import strict_json, validate_proposal
from result_contract import build_summary, write_summary, failure_result
from find_cache_conditions import ROOT, CacheBackend, oracle, parse_args as cache_args
from find_config_conditions import ConfigBackend, parse_args as config_args
from find_prime_conditions import PrimeBackend, parse_args as prime_args


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


@contextmanager
def session_lock(directory):
    path = Path(directory) / "session.lock"
    with path.open("x", encoding="utf-8") as handle:
        handle.write("A workflow command is updating this session.\n")
    try:
        yield
    finally:
        path.unlink()


def adapter(config):
    if config["case"] == "c":
        from c_scalar_backend import bind_contract
        from find_c_conditions import parse_args
        settings = parse_args(["--contract", config["contract"], "--esbmc", config["esbmc"], "--cc", config["cc"],
                               "--timeout", str(config["timeout"]), "--max-seconds", str(config["max_seconds"]),
                               "--max-queries", str(config["max_queries"])])
        return bind_contract(settings.contract), settings
    backend, parser = {"prime": (PrimeBackend, prime_args), "cache": (CacheBackend, cache_args),
                       "config-cache": (ConfigBackend, config_args)}[config["case"]]
    argv = ["--variant", config["variant"], "--esbmc", config["esbmc"], "--cc", config["cc"],
            "--timeout", str(config["timeout"]), "--max-seconds", str(config["max_seconds"]),
            "--max-queries", str(config["max_queries"])]
    if config["case"] == "prime":
        argv += ["--domain", config["domain"]]
    else:
        argv += ["--state-mode", config["state_mode"]]
    return backend, parser(argv)


def fingerprint(config):
    case = {"prime": "prime_lookup", "cache": "same_language_cache", "config-cache": "config_cache", "c": "c_scalar"}[config["case"]]
    paths = [p for p in (ROOT / "tools/find-cond-equiv").glob("*.py") if not p.name.startswith("test_")]
    paths += [ROOT / "tools/verify-equiv" / name for name in ("verify_equiv.py", "c_obligation.py")]
    if config["case"] != "c":
        paths += [p for p in (ROOT / "cases" / case).iterdir() if p.suffix in (".h", ".c", ".json")]
    # Shared imports load these bindings even for stateless cases.
    paths += [ROOT / f"cases/{name}/sketch.json" for name in ("same_language_cache", "config_cache")]
    files = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}
    if config["case"] == "c":
        from c_scalar_contract import Contract
        import pycparser
        files.update(Contract(config["contract"]).identity)
        for path in Path(pycparser.__file__).parent.glob("*.py"):
            files["pycparser/" + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    binaries = {}
    for key in ("esbmc", "cc"):
        path = shutil.which(config[key])
        binaries[key] = None if path is None else {
            "path": str(Path(path).resolve()), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
    return {"files": files, "binaries": binaries, "python": sys.version,
            "contract_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()}


def check_candidate(backend, condition, goal):
    report = {"status": "UNKNOWN", "candidate": condition.expression(),
              "candidate_c": condition.expression(c=True), "checks": {}, "feedback": []}
    inside = [row for row in backend.samples if condition.evaluate(row)]
    bad = next((row for row in inside if row["r_original"] != row["r_cached"]), None)
    if bad is not None:
        report.update(status="REFUTED", reason="native counterexample inside candidate")
        report["feedback"].append({"kind": "unequal_inside", "origin": "native", "input_and_observation": bad})
        return report
    def query(kind, complement=False):
        expression = f"!({report['candidate_c']})" if complement else report["candidate_c"]
        result = backend.query(kind, expression)
        replay = result.get("native_replay")
        if isinstance(replay, dict) and condition.evaluate(replay) == complement:
            return {"status": "UNKNOWN", "reason": "witness outside requested candidate region", "evidence": result}
        return result

    feasible = query("feasible")
    report["checks"]["feasible"] = feasible
    if feasible["status"] not in ("PROVED", "REFUTED"):
        return report
    if feasible["status"] == "PROVED" and inside:
        report["reason"] = "solver/native feasibility disagreement"
        return report
    equal = query("equal")
    report["checks"]["sufficiency"] = equal
    if equal["status"] != "PROVED":
        report["status"] = "REFUTED" if equal["status"] == "REFUTED" else "UNKNOWN"
        report["feedback"].append({"kind": "sufficiency_not_proved", "evidence": equal})
        return report
    if any(condition.evaluate(row) and row["r_original"] != row["r_cached"] for row in backend.samples):
        report["reason"] = "solver/native sufficiency disagreement"
        return report
    if feasible["status"] == "REFUTED":
        report["status"] = "PARTIAL"
        if goal == "sufficient":
            return report
    # Replayed inputs can disprove exactness without another solver call. They
    # never certify universal inequality of the complement.
    outside_equal = next((row for row in backend.samples if not condition.evaluate(row)
                          and row["r_original"] == row["r_cached"]), None)
    if outside_equal is not None:
        report["feedback"].append({"kind": "equal_outside", "origin": "native",
                                   "input_and_observation": outside_equal})
        if feasible["status"] == "PROVED":
            report.update(status="EMPTY_CANDIDATE", reason="empty condition is not a useful sufficient region")
        return report
    different = query("different", complement=True)
    report["checks"]["complement"] = different
    if different["status"] == "PROVED":
        report["status"] = "EXACT"
    else:
        report["feedback"].append({"kind": "complement_not_proved", "evidence": different})
        if feasible["status"] == "PROVED":
            report["status"] = "EMPTY_CANDIDATE" if different["status"] == "REFUTED" else "UNKNOWN"
    return report


def publish(directory, state):
    best = state.get("best_result")
    status = best["status"] if best else "UNKNOWN"
    reached = status == "EXACT" or (state["config"]["goal"] == "sufficient" and status == "PARTIAL")
    summary = {"status": status, "goal_reached": reached, "phase": state["phase"],
               "condition": best["candidate"] if best else None, "scope": state.get("scope"),
               "queries_used": state["queries_used"], "active_seconds": state["active_seconds"],
               "rounds": state["rounds"], "best_result": best, "latest_feedback": state.get("latest_feedback"),
               "artifacts": str(directory), "session_id": state["session_id"],
               "agent_transport": "external JSON files; no LLM API invoked"}
    context = {"schema": 1, "session_id": state["session_id"], "next_round": state["rounds"] + 1,
               "contract": state["config"], "scope": state.get("scope"),
               "model_source": state.get("model_source"), "samples": state.get("samples", []),
               "progress": summary, "identity": state["identity"],
               "proposal_schema": {"session_id": state["session_id"], "round": state["rounds"] + 1,
                                   "condition": True, "seeds": []},
               "condition_grammar": "JSON booleans, supported entry-state atom strings, or {all:[...]}, {any:[...]}, {not:...}",
               "allowed_atoms": state.get("allowed_atoms"),
               "instructions": "Propose a condition and optional entry-state inputs. true in the schema is only a syntax example. "
                               "Stop if progress.goal_reached is true. "
                               "Read source and feedback; do not assume it is correct. Do not edit runner-owned session files, "
                               "sources, scope, assumptions or verification flags. Submit only a separate proposal JSON. "
                               "No verdicts, output labels, code or expected-answer files are accepted."}
    save(directory / "session.json", state)
    save(directory / "result.json", summary)
    save(directory / "agent-context.json", context)
    normalized = build_summary(summary, producer="agent", samples=state.get("samples", []), state=state)
    write_summary(directory, normalized)
    print(f"{summary['status']}: {summary['condition']}")
    print(f"Phase: {summary['phase']}; goal reached: {summary['goal_reached']}")
    if state.get("latest_feedback"):
        print(f"Latest proposal: {state['latest_feedback']['status']}")
    print(f"Agent context: {directory / 'agent-context.json'}")
    print(f"Report: {directory / 'report.md'}")
    return summary


def record_backend(directory, state, backend, started):
    if backend:
        state["queries_used"] += len(backend.queries)
        state["samples"] = backend.samples
        save(directory / "queries.json", backend.queries)
        save(directory / "replays.json", backend.replays)
        save(directory / "traces.json", backend.samples)
    state["active_seconds"] += time.monotonic() - started


def start(config, root):
    backend_type, settings = adapter(config)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="session-", dir=root))
    phase = directory / "round-000"
    phase.mkdir()
    state = {"schema": 1, "session_id": str(uuid.uuid4()), "config": config,
             "created_utc": datetime.now(timezone.utc).isoformat(), "identity": fingerprint(config),
             "rounds": 0, "queries_used": 0, "active_seconds": 0.0, "phase": "UNKNOWN", "best_result": None}
    backend = None
    started = time.monotonic()
    with session_lock(directory):
        try:
            backend = backend_type(settings, phase)
            state.update(scope=backend.scope, model_source=backend.model,
                         allowed_atoms={"numeric_fields": list(backend.numeric_fields),
                                        "examples": [atom.text() for atom in backend.initial_atoms()],
                                        "modulo": "x % d == r, 2<=d<=16 and 0<=r<d" if config["case"] == "prime" else None})
            backend.prepare()
            state["esbmc_version_output"] = backend.version
            obligations = backend.state_obligations() if backend.proof_before_replay else None
            if obligations is not None:
                state["state_obligations"] = obligations
                if any(row["status"] != "PROVED" for row in obligations.values()):
                    raise RuntimeError("whole-domain safety/unwinding not proved; native replay disabled")
            backend.replay(backend.default_seeds(settings.state_mode))
            if obligations is None:
                obligations = backend.state_obligations()
            state["state_obligations"] = obligations
            if any(row["status"] != "PROVED" for row in obligations.values()):
                raise RuntimeError("state initialization/preservation not proved")
            feasible = backend.query("feasible")
            state["domain_feasibility"] = feasible
            state["phase"] = {"REFUTED": "READY", "PROVED": "EMPTY_DOMAIN"}.get(feasible["status"], "UNKNOWN")
            if feasible["status"] == "PROVED" and backend.samples:
                raise RuntimeError("solver/native domain-feasibility disagreement")
            if fingerprint(config) != state["identity"]:
                raise RuntimeError("source or tool identity changed during initialization")
        except (OSError, ValueError, RuntimeError) as exc:
            state.update(phase="UNKNOWN", latest_feedback={"status": "UNKNOWN", "reason": str(exc)})
            if getattr(exc, "code", None):
                state["latest_feedback"]["reason_code"] = exc.code
        finally:
            record_backend(phase, state, backend, started)
        return directory, publish(directory, state)


def step(directory, proposal_path):
    directory = Path(directory).resolve()
    with session_lock(directory):
        state = strict_json((directory / "session.json").read_text(encoding="utf-8"))
        config = state["config"]
        if state["phase"] != "READY":
            raise ValueError("session is not ready; inspect initialization and start a new session")
        if state["rounds"] >= config["max_rounds"]:
            raise ValueError("session round budget exhausted")
        try:
            unchanged = fingerprint(config) == state["identity"]
        except (OSError, ValueError, RuntimeError, RecursionError):
            unchanged = False
        if not unchanged:
            state.update(phase="BLOCKED", best_result=None,
                         latest_feedback={"status": "UNKNOWN", "reason": "source or tool identity changed; start a new session"})
            return publish(directory, state)
        backend_type, settings = adapter(config)
        phase = directory / f"round-{state['rounds'] + 1:03d}"
        phase.mkdir()
        backend = None
        started = time.monotonic()
        result = {"status": "REJECTED"}
        try:
            with Path(proposal_path).open("rb") as handle:
                data = handle.read(65537)
            if len(data) > 65536:
                raise ValueError("proposal exceeds 64 KiB")
            (phase / "proposal.json").write_bytes(data)
            condition, seeds = validate_proposal(strict_json(data.decode("utf-8")), state, backend_type, settings)
            result["status"] = "UNKNOWN"
            remaining = config["max_seconds"] - state["active_seconds"]
            settings.max_queries = config["max_queries"] - state["queries_used"]
            if remaining <= 0 or settings.max_queries <= 0:
                raise RuntimeError("session query or active-time budget exhausted")
            backend = backend_type(settings, phase)
            backend.deadline = started + remaining
            backend.prepare()
            backend.restore_obligations(state.get("state_obligations", {}))
            # Re-execute persisted entry inputs; never import supplied output labels.
            old_inputs = [{name: row[name] for name in backend.fields} for row in state.get("samples", [])]
            backend.replay(old_inputs, origin="prior_round_inputs")
            backend.replay(seeds, origin="agent_proposal")
            result = check_candidate(backend, condition, config["goal"])
        except (OSError, ValueError, RuntimeError, RecursionError) as exc:
            result["reason"] = str(exc)
            if getattr(exc, "code", None):
                result["reason_code"] = exc.code
            # Only validation failures before backend creation are REJECTED.
            if backend is not None:
                result["status"] = "UNKNOWN"
        finally:
            record_backend(phase, state, backend, started)
        # Check on failed rounds too, so an intervening edit/compile failure
        # cannot publish an earlier certificate as current for changed inputs.
        try:
            unchanged = fingerprint(config) == state["identity"]
        except (OSError, ValueError, RuntimeError, RecursionError):
            unchanged = False
        if not unchanged:
            state.update(phase="BLOCKED", best_result=None)
            result = {"status": "UNKNOWN", "reason": "source, contract or tool identity changed during checking"}
        state["rounds"] += 1
        result["round"] = state["rounds"]
        result["artifacts"] = str(phase)
        state["latest_feedback"] = result
        if result["status"] in ("PARTIAL", "EXACT") and (not state["best_result"] or state["best_result"]["status"] != "EXACT"):
            state["best_result"] = result
        save(phase / "result.json", result)
        return publish(directory, state)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    begin = actions.add_parser("start")
    begin.add_argument("--case", choices=("prime", "cache", "config-cache", "c"), default="prime")
    begin.add_argument("--variant")
    begin.add_argument("--contract", help="--case c only: fixed scalar C contract JSON")
    begin.add_argument("--domain", help="prime only; default 0:127")
    begin.add_argument("--state-mode", choices=("empty", "invariant"), default="invariant")
    begin.add_argument("--goal", choices=("exact", "sufficient"), default="exact")
    begin.add_argument("--esbmc", default=oracle.DEFAULT_ESBMC)
    begin.add_argument("--cc", default="cc")
    begin.add_argument("--timeout", type=float, default=30)
    begin.add_argument("--max-seconds", type=float, default=300)
    begin.add_argument("--max-queries", type=int, default=64)
    begin.add_argument("--max-rounds", type=int, default=8)
    begin.add_argument("--workdir", default=".verify-equiv-runs/agent-workflow")
    advance = actions.add_parser("step")
    advance.add_argument("--session", required=True)
    advance.add_argument("--proposal", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "step":
            result = step(args.session, args.proposal)
            return 0 if result["goal_reached"] else 2
        config = {key: value for key, value in vars(args).items() if key not in ("action", "workdir")}
        if args.case == "c":
            if not args.contract or args.variant is not None or args.domain is not None or args.state_mode != "invariant":
                parser.error("--case c requires --contract; variant/domain/state-mode are fixed by that contract")
            config.update(contract=str(Path(args.contract).resolve()), variant="pair", state_mode="stateless")
        elif args.contract is not None or args.variant is None:
            parser.error("built-in cases require --variant and do not accept --contract")
        if not 1 <= args.max_rounds <= 64 or args.max_queries < 4 or not all(
                math.isfinite(n) and n > 0 for n in (args.timeout, args.max_seconds)):
            parser.error("positive time budgets, >=4 queries and 1..64 rounds required")
        if args.case != "prime" and args.domain is not None:
            parser.error("--domain is prime-only; cache state contracts are fixed by --state-mode")
        if args.case == "prime" and args.state_mode != "invariant":
            parser.error("prime is stateless; --state-mode empty does not apply")
        config["domain"] = args.domain or ("0:127" if args.case == "prime" else None)
        directory, result = start(config, args.workdir)
        print(f"Session: {directory}")
        return 0 if result["phase"] == "READY" else 2
    except (OSError, ValueError, RuntimeError) as exc:
        if args.action == "start":
            failure_result(args, exc, producer="agent")
        print(f"Workflow error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
