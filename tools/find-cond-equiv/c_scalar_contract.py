"""Strict, deliberately small C frontend; source bodies are never synthesized.

The parser validates scalar functions, local constant tables and opt-in bounded
array parameters. The harness
uses the original bodies, with function names scoped by checked macro bindings.
This is an admission checker, not a sandbox for hostile files or compilers.
"""
import hashlib
from pathlib import Path
import re

from agent_conditions import strict_json
from predicate_search import UINT32_MAX
from result_contract import InputFailure


def identifier(value):
    return (isinstance(value, str) and re.fullmatch(r"[a-z][A-Za-z0-9_]{0,47}", value)
            and not value.startswith(("ce_", "finder_"))
            and value not in {"true", "false", "bool", "uint32_t"})


def stripped_source(source):
    # Reject line splicing and alternate preprocessing tokens before parsing.
    if "\\" in source or "??" in source or "%:" in source or "\x00" in source:
        raise ValueError("unsupported C: escapes, line splicing or alternate preprocessing tokens")
    # Literals are outside this subset; comments can contain arbitrary quotes.
    tokens = re.compile(r'/\*.*?\*/|//[^\n]*|"[^"\n]*"|\'[^\'\n]*\'', re.S)
    def replace(match):
        token = match.group()
        if token.startswith(("/*", "//")):
            return " " + "\n" * token.count("\n")
        raise ValueError("unsupported C: string/character literals")
    clean = tokens.sub(replace, source)
    lines = []
    for line in clean.splitlines():
        if line.lstrip().startswith("#"):
            if not re.fullmatch(r"\s*#\s*include\s*<(stdint|stdbool)\.h>\s*", line):
                raise ValueError("unsupported C: only stdint.h/stdbool.h includes are allowed")
            line = ""
        lines.append(line)
    return "\n".join(lines)


class Source:
    def __init__(self, path, *, array_parameters=False):
        try:
            from pycparser import c_ast, c_parser
        except ImportError as exc:
            raise InputFailure("DEPENDENCY_MISSING", "C scalar frontend requires: python3 -m pip install -r tools/find-cond-equiv/requirements.txt") from exc
        self.ast = c_ast
        self.array_parameters = array_parameters
        self.path = Path(path).resolve()
        self.data = self.path.read_bytes()
        if len(self.data) > 65536:
            raise ValueError("unsupported C: source exceeds 64 KiB")
        self.text = self.data.decode("utf-8")
        self.body = stripped_source(self.text)
        try:
            tree = c_parser.CParser().parse("typedef unsigned int uint32_t; typedef _Bool bool;\n" + self.body)
        except Exception as exc:
            raise ValueError(f"unsupported C syntax in {self.path.name}: {exc}") from exc
        functions = tree.ext[2:]
        if not 1 <= len(functions) <= 16 or any(not isinstance(f, c_ast.FuncDef) for f in functions):
            raise ValueError("unsupported C: only 1..16 function definitions; no globals/prototypes/typedefs")
        self.names = [f.decl.name for f in functions]
        if len(set(self.names)) != len(self.names) or not all(identifier(n) for n in self.names):
            raise ValueError("unsupported or duplicate function name")
        self.signatures = {}
        self.tables = []
        self.table_elements = 0
        self.nodes = 0
        for function in functions:
            decl = function.decl
            self.current_function = decl.name
            if decl.storage not in ([], ["static"]) or decl.funcspec or decl.quals or function.param_decls:
                raise ValueError("unsupported function declaration")
            result_type = self.scalar_type(decl.type.type)
            params = decl.type.args.params if decl.type.args else []
            if not 1 <= len(params) <= 4:
                raise ValueError("functions require 1..4 parameters")
            env = {}
            types = []
            for param in params:
                if not isinstance(param, c_ast.Decl) or param.storage or param.init or param.funcspec or param.align:
                    raise ValueError("unsupported parameter declaration")
                self.check_name(param.name, env)
                if array_parameters and isinstance(param.type, c_ast.ArrayDecl):
                    array = param.type
                    if param.quals not in ([], ["const"]) or array.dim_quals:
                        raise ValueError("unsupported array parameter qualifiers")
                    element = self.scalar_type(array.type, const=bool(param.quals))
                    size = self.array_size(array.dim, 4)
                    env[param.name] = ("array", element, size, bool(param.quals))
                else:
                    if param.quals:
                        raise ValueError("unsupported scalar parameter qualifier")
                    env[param.name] = self.scalar_type(param.type)
                types.append(env[param.name])
            # The current function is deliberately absent: recursion is rejected.
            self.statement(function.body, env, result_type)
            if not self.returns(function.body):
                raise ValueError("every function must structurally return a value on every path")
            self.signatures[decl.name] = (result_type, types)

    def scalar_type(self, node, *, const=False):
        a = self.ast
        if not isinstance(node, a.TypeDecl) or node.quals != (["const"] if const else []) or not isinstance(node.type, a.IdentifierType):
            raise ValueError("unsupported C type: only unqualified uint32_t/bool scalars")
        names = node.type.names
        if names == ["uint32_t"]:
            return "uint32_t"
        if names in (["bool"], ["_Bool"]):
            return "bool"
        raise ValueError("unsupported C type: only uint32_t/bool")

    def array_size(self, node, maximum):
        if not isinstance(node, self.ast.Constant) or not re.fullmatch(r"[1-9][0-9]*[uU]?", node.value):
            raise ValueError("array length must be an explicit positive decimal literal")
        size = int(node.value.rstrip("uU"))
        if not 1 <= size <= maximum:
            raise ValueError(f"array length must be 1..{maximum}")
        return size

    def table_declaration(self, node, env):
        """Admit only fully initialized, automatic, one-dimensional const tables.

        Tables never decay to pointers in the admitted language. Index safety is
        a whole-domain ESBMC obligation before any native input is executed.
        """
        a = self.ast
        array = node.type
        if node.storage or node.quals != ["const"] or node.funcspec or node.bitsize or node.align or array.dim_quals:
            raise ValueError("tables must be automatic const arrays without extra qualifiers")
        element = self.scalar_type(array.type, const=True)
        if not isinstance(array.dim, a.Constant) or not re.fullmatch(r"[1-9][0-9]*[uU]?", array.dim.value):
            raise ValueError("table length must be an explicit positive decimal literal")
        size = int(array.dim.value.rstrip("uU"))
        if not 1 <= size <= 256 or self.table_elements + size > 256:
            raise ValueError("at most 256 table elements per source are supported")
        if not isinstance(node.init, a.InitList) or len(node.init.exprs or []) != size:
            raise ValueError("table initializer must explicitly provide every element")
        for value in node.init.exprs:
            if not (isinstance(value, a.Constant) or isinstance(value, a.ID) and value.name in ("true", "false")):
                raise ValueError("table elements must be literal constants")
            if self.expression(value, env) != element:
                raise ValueError("table initializer element type mismatch")
        self.table_elements += size
        self.tables.append({"function": self.current_function, "name": node.name,
                            "element_type": element, "length": size})
        env[node.name] = ("table", element, size)

    def check_name(self, name, env):
        if not identifier(name) or name in env or name in self.names:
            raise ValueError("unsupported identifier, shadowing or function-name collision")

    def tick(self):
        self.nodes += 1
        if self.nodes > 4096:
            raise ValueError("unsupported C: AST exceeds 4096 checked nodes")

    def expression(self, node, env):
        self.tick()
        a = self.ast
        if isinstance(node, a.ID):
            if node.name in ("true", "false"):
                return "bool"
            if node.name not in env:
                raise ValueError(f"unknown scalar: {node.name}")
            if isinstance(env[node.name], tuple):
                raise ValueError("tables may only be used in indexed reads; pointer decay is unsupported")
            return env[node.name]
        if isinstance(node, a.ArrayRef) and isinstance(node.name, a.ID):
            table = env.get(node.name.name)
            if not isinstance(table, tuple) or table[0] not in ("table", "array"):
                raise ValueError("indexed reads require an admitted array")
            if self.expression(node.subscript, env) != "uint32_t":
                raise ValueError("table indices must have uint32_t type")
            return table[1]
        if isinstance(node, a.Constant):
            # No signed arithmetic or implementation-dependent literal types.
            if not re.fullmatch(r"(?:0[xX][0-9a-fA-F]+|0[0-7]*|[1-9][0-9]*)[uU]", node.value):
                raise ValueError("integer literals require a uint32 unsigned suffix, e.g. 1u")
            text = node.value[:-1]
            value = int(text, 16 if text.lower().startswith("0x") else 8 if text.startswith("0") else 10)
            if value > UINT32_MAX:
                raise ValueError("integer literal exceeds uint32_t")
            return "uint32_t"
        if isinstance(node, a.Cast):
            self.expression(node.expr, env)
            return self.scalar_type(node.to_type.type)
        if isinstance(node, a.UnaryOp) and node.op in ("!", "~", "+", "-"):
            typ = self.expression(node.expr, env)
            if node.op == "!":
                return "bool"
            if typ != "uint32_t":
                raise ValueError("arithmetic requires uint32_t operands")
            return typ
        if isinstance(node, a.BinaryOp):
            left, right = self.expression(node.left, env), self.expression(node.right, env)
            if node.op in ("&&", "||", "==", "!=", "<", "<=", ">", ">="):
                return "bool"
            if left != "uint32_t" or right != "uint32_t" or node.op not in ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>"):
                raise ValueError("unsupported arithmetic; operands must be uint32_t")
            if node.op in ("<<", ">>"):
                if not isinstance(node.right, a.Constant) or not re.fullmatch(r"(?:[0-9]|[12][0-9]|3[01])[uU]", node.right.value):
                    raise ValueError("shift count must be a decimal unsigned literal in 0..31")
            return "uint32_t"
        if isinstance(node, a.TernaryOp):
            self.expression(node.cond, env)
            left, right = self.expression(node.iftrue, env), self.expression(node.iffalse, env)
            if left != right:
                raise ValueError("conditional branches require identical scalar types")
            return left
        if isinstance(node, a.FuncCall) and isinstance(node.name, a.ID):
            signature = self.signatures.get(node.name.name)
            if signature is None:
                raise ValueError("unsupported call: helpers must be defined earlier; no external calls or recursion")
            args = node.args.exprs if isinstance(node.args, a.ExprList) else []
            if [self.expression(arg, env) for arg in args] != signature[1]:
                raise ValueError("helper argument types/count do not match")
            return signature[0]
        raise ValueError(f"unsupported C expression: {type(node).__name__}")

    def statement(self, node, env, result_type):
        self.tick()
        a = self.ast
        if node is None or isinstance(node, a.EmptyStatement):
            return
        if isinstance(node, a.Compound):
            local = dict(env)
            for child in node.block_items or []:
                self.statement(child, local, result_type)
            return
        if isinstance(node, a.DeclList):
            for child in node.decls:
                self.statement(child, env, result_type)
            return
        if isinstance(node, a.Decl):
            self.check_name(node.name, env)
            if isinstance(node.type, a.ArrayDecl):
                self.table_declaration(node, env)
                return
            typ = self.scalar_type(node.type)
            if node.storage or node.quals or node.funcspec or node.bitsize or node.init is None:
                raise ValueError("locals must be initialized automatic scalars")
            if self.expression(node.init, env) != typ:
                raise ValueError("local initializer type mismatch; use an explicit scalar cast")
            env[node.name] = typ
            return
        if isinstance(node, a.Return):
            if self.expression(node.expr, env) != result_type:
                raise ValueError("return type mismatch; use an explicit scalar cast")
            return
        if isinstance(node, a.Assignment) and isinstance(node.lvalue, (a.ID, a.ArrayRef)):
            if isinstance(node.lvalue, a.ArrayRef):
                self.check_array_write(node.lvalue, env)
            left, right = self.expression(node.lvalue, env), self.expression(node.rvalue, env)
            if left != right or node.op not in ("=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=") or (node.op != "=" and left != "uint32_t"):
                raise ValueError("unsupported scalar assignment")
            return
        if isinstance(node, a.UnaryOp) and node.op in ("p++", "p--", "++", "--") and isinstance(node.expr, a.ID):
            if self.expression(node.expr, env) != "uint32_t":
                raise ValueError("increments require uint32_t")
            return
        if isinstance(node, a.If):
            self.expression(node.cond, env)
            self.statement(node.iftrue, dict(env), result_type)
            self.statement(node.iffalse, dict(env), result_type)
            return
        if isinstance(node, a.While):
            self.expression(node.cond, env)
            self.statement(node.stmt, dict(env), result_type)
            return
        if isinstance(node, a.For):
            local = dict(env)
            self.statement(node.init, local, result_type)
            if node.cond is not None:
                self.expression(node.cond, local)
            self.statement(node.next, local, result_type)
            self.statement(node.stmt, local, result_type)
            return
        if isinstance(node, a.FuncCall):
            self.expression(node, env)
            return
        raise ValueError(f"unsupported C statement: {type(node).__name__}")

    def check_array_write(self, node, env):
        value = env.get(node.name.name) if isinstance(node.name, self.ast.ID) else None
        if not isinstance(value, tuple) or value[0] != "array" or value[3]:
            raise ValueError("writes require a mutable bounded array parameter")

    def returns(self, node):
        a = self.ast
        if isinstance(node, a.Return):
            return True
        if isinstance(node, a.Compound):
            return bool(node.block_items) and self.returns(node.block_items[-1])
        if isinstance(node, a.If):
            return self.returns(node.iftrue) and self.returns(node.iffalse)
        return False

    def namespaced(self, side):
        return ("\n".join(f"#define {name} ce_{side}_{name}" for name in self.names)
                + "\n" + self.body + "\n"
                + "\n".join(f"#undef {name}" for name in self.names) + "\n")


class Contract:
    def __init__(self, path):
        self.path = Path(path).resolve()
        raw = self.path.read_bytes()
        if len(raw) > 65536:
            raise ValueError("contract exceeds 64 KiB")
        self.data = d = strict_json(raw.decode("utf-8"))
        required = {"schema", "name", "original", "candidate", "inputs", "return_type", "observations", "unwind"}
        if not isinstance(d, dict) or set(d) != required or type(d["schema"]) is not int or d["schema"] not in (1, 2):
            raise ValueError("invalid C contract schema: use 1 for scalars or 2 for bounded arrays")
        if not identifier(d["name"]) or d["return_type"] not in ("bool", "uint32_t"):
            raise ValueError("contract requires a name and bool/uint32_t return")
        if type(d["unwind"]) is not int or not 1 <= d["unwind"] <= 1024:
            raise ValueError("unwind must be 1..1024; unwinding assertions remain enabled")
        if not isinstance(d["inputs"], dict) or not 1 <= len(d["inputs"]) <= 4:
            raise ValueError("contract requires 1..4 input bindings")
        self.input_specs = {}
        self.arrays = {}
        empty_fields = []
        for name, spec in d["inputs"].items():
            if not identifier(name) or not isinstance(spec, dict):
                raise ValueError("invalid input name or specification")
            is_array = spec.get("type") in ("uint32_t[]", "bool[]")
            keys = {"type", "length", "min", "max"} if is_array else {"type", "min", "max"}
            if set(spec) != keys or (not is_array and spec["type"] not in ("bool", "uint32_t")):
                raise ValueError("each input requires type, min/max, and length only for arrays")
            if is_array:
                if d["schema"] != 2 or type(spec["length"]) is not int or not 1 <= spec["length"] <= 4:
                    raise ValueError("array inputs require schema 2 and literal length 1..4")
                self.arrays[name] = spec
            element = spec["type"][:-2] if is_array else spec["type"]
            limit = 1 if element == "bool" else UINT32_MAX
            if type(spec["min"]) is not int or type(spec["max"]) is not int or not (0 <= spec["min"] <= limit and 0 <= spec["max"] <= limit):
                raise ValueError("invalid scalar input domain")
            if spec["min"] > spec["max"]:
                empty_fields.append(name)
            names = [f"{name}_{i}" for i in range(spec["length"])] if is_array else [name]
            for field in names:
                if not identifier(field) or field in self.input_specs or field in (
                        "r_original", "r_cached", "observations_original", "observations_candidate"):
                    raise ValueError("flattened input names collide or exceed identifier limits")
                self.input_specs[field] = {"type": element, "min": spec["min"], "max": spec["max"]}
        if not 1 <= len(self.input_specs) <= 4:
            raise ValueError("at most four scalar input values, including array elements, are supported")
        if d["schema"] == 2 and not self.arrays:
            raise ValueError("schema 2 requires at least one array input")
        if d["observations"] != ["return", *self.arrays]:
            raise ValueError("observe return followed by every array in input declaration order")
        self.fields = tuple(self.input_specs)
        if empty_fields:
            raise InputFailure("EMPTY_DOMAIN", "empty inclusive input range: " + ", ".join(empty_fields),
                               {"language": "C", "inputs": d["inputs"], "observations": d["observations"],
                                "source_admission": "not completed; no program equivalence claim"})
        self.sources = {}
        for side in ("original", "candidate"):
            binding = d[side]
            if not isinstance(binding, dict) or set(binding) != {"source", "entry", "args"} or not isinstance(binding["source"], str) or not identifier(binding["entry"]):
                raise ValueError("each side requires source, entry and args")
            args = binding["args"]
            if not isinstance(args, list) or any(not isinstance(n, str) for n in args) or len(args) != len(d["inputs"]) or set(args) != set(d["inputs"]):
                raise ValueError("each side must bind every logical input exactly once")
            try:
                source = Source(self.path.parent / binding["source"], array_parameters=d["schema"] == 2)
            except RecursionError as exc:
                raise InputFailure("UNSUPPORTED_INPUT", "unsupported C: nesting too deep") from exc
            except InputFailure:
                raise
            except ValueError as exc:
                raise InputFailure("UNSUPPORTED_INPUT", f"{side} source {binding['source']}: {exc}") from exc
            signature = source.signatures.get(binding["entry"])
            actual = None if signature is None else (signature[0], [
                (t[1] + "[]", t[2]) if isinstance(t, tuple) else t for t in signature[1]])
            wanted = (d["return_type"], [(d["inputs"][n]["type"], d["inputs"][n]["length"])
                                       if n in self.arrays else d["inputs"][n]["type"] for n in args])
            if actual != wanted:
                raise ValueError(f"{side} entry signature does not match contract")
            self.sources[side] = source
        self.identity = {str(self.path): hashlib.sha256(raw).hexdigest(), **{
            str(s.path): hashlib.sha256(s.data).hexdigest() for s in self.sources.values()}}

    def call(self, side):
        binding = self.data[side]
        return f"ce_{side}_{binding['entry']}(" + ", ".join(
            f"ce_buf_{side}_{n}" if n in self.arrays else "finder_" + n for n in binding["args"]) + ")"

    def argument_copies(self):
        return [f"  {spec['type'][:-2]} ce_buf_{side}_{name}[{spec['length']}] = {{"
                + ", ".join(f"finder_{name}_{i}" for i in range(spec["length"])) + "};"
                for side in ("original", "candidate") for name, spec in self.arrays.items()]

    def observation_values(self, side):
        return ["ce_left" if side == "original" else "ce_right", *[
            f"ce_buf_{side}_{name}[{i}]" for name, spec in self.arrays.items() for i in range(spec["length"])]]

    def observation_types(self):
        return [self.data["return_type"], *[spec["type"][:-2] for spec in self.arrays.values() for _ in range(spec["length"])]]

    def equality(self):
        return " && ".join(f"({a} == {b})" for a, b in zip(self.observation_values("original"), self.observation_values("candidate")))

    def model(self):
        return ("#include <stdint.h>\n#include <stdbool.h>\n#include <limits.h>\n"
                '_Static_assert(CHAR_BIT == 8 && UINT_MAX == UINT32_MAX && INT_MAX == 2147483647, "32-bit int model required");\n'
                '_Static_assert(_Generic((uint32_t)0, unsigned int: 1, default: 0), "uint32_t must be unsigned int");\n'
                + "".join(source.namespaced(side) for side, source in self.sources.items()))
