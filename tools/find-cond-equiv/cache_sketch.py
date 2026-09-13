"""Reviewed private-cache proof template. Bindings are data, never proof results.

The invariant implementation remains supplied C; this module does not discover
invariants or transfer solver certificates between instances.
"""
import hashlib
import json
from pathlib import Path
import re

PROPERTIES = {"feasible": "__FINDER_FEASIBLE__", "equal": "__VERIFY_EQUIV_RELATIONAL_PROPERTY__",
              "different": "__FINDER_ALL_DIFFERENT__", "init": "__FINDER_INITIALIZED__",
              "preservation": "__FINDER_PRESERVED__", "expected": "__FINDER_EXPECTED_CONDITION__"}


class CacheSketch:
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.validate()

    def validate(self):
        data = self.data
        required = {"schema", "name", "fields", "state_fields", "call_args", "initial_state", "variants"}
        if not isinstance(data, dict) or set(data) != required or type(data["schema"]) is not int or data["schema"] != 1:
            raise ValueError("invalid cache sketch binding schema")
        identifier = lambda name: isinstance(name, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name)
        if not identifier(data["name"]):
            raise ValueError("invalid sketch name")
        fields = data["fields"]
        if not isinstance(fields, dict) or not fields or any(
                not identifier(name) or kind not in ("bool", "uint32_t") for name, kind in fields.items()):
            raise ValueError("only named bool/uint32_t fields are supported")
        for key in ("state_fields", "call_args"):
            names = data[key]
            if not isinstance(names, list) or not names or any(not isinstance(name, str) or name not in fields for name in names):
                raise ValueError("state fields and call arguments must name declared fields")
            if len(set(names)) != len(names):
                raise ValueError("duplicate binding field")
        if set(data["state_fields"]) & set(data["call_args"]) or set(data["state_fields"] + data["call_args"]) != set(fields):
            raise ValueError("each field must belong to state or call arguments exactly once")
        initial = data["initial_state"]
        if not isinstance(initial, dict) or set(initial) != set(data["state_fields"]):
            raise ValueError("initial state must initialize every cache field")
        for name, value in initial.items():
            if type(value) is not int or not 0 <= value <= (1 if fields[name] == "bool" else 2**32-1):
                raise ValueError("initial state value outside declared type")
        variants = data["variants"]
        if not isinstance(variants, dict) or not variants or any(
                not identifier(name) or not identifier(function) for name, function in variants.items()):
            raise ValueError("variant bindings must be function identifiers")

    def literal(self, field):
        value = self.data["initial_state"][field]
        return ("true" if value else "false") if self.data["fields"][field] == "bool" else f"UINT32_C({value})"

    def cache_initializer(self, symbolic):
        # Designated initializers bind names instead of silently trusting struct order.
        return ", ".join(f".{field} = " + (f"finder_{field}" if symbolic else self.literal(field))
                         for field in self.data["state_fields"])

    def render(self, model, variant, state_mode, kind, condition="true", expected=None):
        if variant not in self.data["variants"] or state_mode not in ("empty", "invariant") or kind not in PROPERTIES:
            raise ValueError("unknown sketch variant, state mode or obligation")
        if kind == "init":
            body = f'Cache cache = {{{self.cache_initializer(False)}}};\n__ESBMC_assert(invariant(&cache), "{PROPERTIES[kind]}");'
        else:
            lines = []
            for field, ctype in self.data["fields"].items():
                value = self.literal(field) if state_mode == "empty" and field in self.data["state_fields"] else (
                    "nondet_bool()" if ctype == "bool" else "nondet_u32()")
                lines.append(f"{ctype} finder_{field} = {value};")
            lines += [f"Cache cache = {{{self.cache_initializer(True)}}};",
                      "__ESBMC_assume(invariant(&cache));", f"__ESBMC_assume({condition});"]
            if kind == "feasible":
                lines.append(f'__ESBMC_assert(false, "{PROPERTIES[kind]}");')
            elif kind == "expected":
                if expected is None:
                    raise ValueError("expected-condition obligation requires an expression")
                lines.append(f'__ESBMC_assert({expected}, "{PROPERTIES[kind]}");')
            else:
                args = ", ".join("finder_" + field for field in self.data["call_args"])
                lines += [f"uint32_t r_original = original({args});",
                          f"uint32_t r_cached = {self.data['variants'][variant]}(&cache, {args});",
                          f'__ESBMC_assert(invariant(&cache), "{PROPERTIES["preservation"]}");']
                if kind in ("equal", "different"):
                    relation = "==" if kind == "equal" else "!="
                    lines.append(f'__ESBMC_assert(r_original {relation} r_cached, "{PROPERTIES[kind]}");')
            body = "\n".join(lines)
        return model + "\nextern uint32_t nondet_u32(void);\nextern bool nondet_bool(void);\n" + \
            "extern void __ESBMC_assume(bool);\nextern void __ESBMC_assert(bool, const char *);\n" + \
            "void finder_entry(void)\n{\n" + body + "\n}\n"

    def manifest(self):
        binding = json.dumps(self.data, sort_keys=True, separators=(",", ":")).encode()
        return {"template": "private-cache-v1", "binding": self.data,
                "binding_sha256": hashlib.sha256(binding).hexdigest(),
                "template_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "obligations": PROPERTIES,
                "trusted_manual_inputs": ["C model", "invariant", "field/call bindings", "scope", "predicate vocabulary"],
                "reuse": "obligation generation only; all solver obligations rerun for each instance",
                "sequence_claim": "none; reported conditions describe one call under the supplied invariant"}
