import ast
import re
import z3
from pathlib import Path


INT32_MIN = -(2 ** 31)
INT32_MAX = 2 ** 31 - 1


def expression_to_z3(text, env):
    """
    Tiny expression translator for the first PoC.
    Supports:
      variables
      integer constants
      + - *
      < <= > >= == !=
    """

    tree = ast.parse(text.strip(), mode="eval").body

    def conv(node):

        if isinstance(node, ast.Name):
            return env[node.id]

        if isinstance(node, ast.Constant):
            if isinstance(node.value, int):
                return z3.IntVal(node.value)

        if isinstance(node, ast.BinOp):
            a = conv(node.left)
            b = conv(node.right)

            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b

        if isinstance(node, ast.Compare):
            assert len(node.ops) == 1
            assert len(node.comparators) == 1

            a = conv(node.left)
            b = conv(node.comparators[0])
            op = node.ops[0]

            if isinstance(op, ast.Lt):
                return a < b
            if isinstance(op, ast.LtE):
                return a <= b
            if isinstance(op, ast.Gt):
                return a > b
            if isinstance(op, ast.GtE):
                return a >= b
            if isinstance(op, ast.Eq):
                return a == b
            if isinstance(op, ast.NotEq):
                return a != b

        raise RuntimeError(
            f"Unsupported expression in first PoC: {ast.dump(node)}"
        )

    return conv(tree)


def parse_if_return_function(path, x):
    """
    Parse the first deliberately-small GOTO subset:

        IF !(cond) THEN GOTO 1
        RETURN: expr1
     1: RETURN: expr2

    Produces:
        If(cond, expr1, expr2)
    """

    text = Path(path).read_text()

    cond_match = re.search(
        r'IF !\((.*?)\) THEN GOTO\s+(\d+)',
        text
    )

    if not cond_match:
        raise RuntimeError(f"No conditional found in {path}")

    condition_text = cond_match.group(1)
    target_label = cond_match.group(2)

    after_if = text[cond_match.end():]

    first_return = re.search(
        r'RETURN:\s*(.+)',
        after_if
    )

    if not first_return:
        raise RuntimeError(f"No first return found in {path}")

    true_expr_text = first_return.group(1).strip()

    label_return = re.search(
        rf'{re.escape(target_label)}:\s*RETURN:\s*(.+)',
        after_if
    )

    if not label_return:
        raise RuntimeError(
            f"No return for label {target_label} in {path}"
        )

    false_expr_text = label_return.group(1).strip()

    env = {"x": x}

    cond = expression_to_z3(
        condition_text,
        env
    )

    true_expr = expression_to_z3(
        true_expr_text,
        env
    )

    false_expr = expression_to_z3(
        false_expr_text,
        env
    )

    return z3.If(
        cond,
        true_expr,
        false_expr
    )


def check_pair(name, python_path, c_path):

    x = z3.Int("x")

    py_out = parse_if_return_function(
        python_path,
        x
    )

    c_out = parse_if_return_function(
        c_path,
        x
    )

    # Shared input domain:
    # Python model is wider, C function takes signed int.
    domain = z3.And(
        x >= INT32_MIN,
        x <= INT32_MAX
    )

    eq = z3.simplify(
        py_out == c_out
    )

    print()
    print("=" * 70)
    print(name)
    print("=" * 70)

    print("Python output relation:")
    print(z3.simplify(py_out))

    print()
    print("C output relation:")
    print(z3.simplify(c_out))

    print()
    print("Raw equivalence predicate:")
    print(eq)

    # Find counterexample.
    solver = z3.Solver()

    solver.add(domain)
    solver.add(py_out != c_out)

    result = solver.check()

    print()
    print("Counterexample query:")
    print(result)

    if result == z3.sat:
        model = solver.model()
        print("Counterexample x =", model[x])
    else:
        print("No counterexample in shared int32 domain.")

    # Test x < 100 as candidate safe region.
    safe = z3.Solver()

    safe.add(domain)
    safe.add(x < 100)
    safe.add(py_out != c_out)

    print()
    print("Candidate region x < 100:")
    print("mismatch query =", safe.check())

    if safe.check() == z3.unsat:
        print("PROVED: x < 100 is an equivalence region.")

    # See whether x >= 100 contains disagreement.
    outside = z3.Solver()

    outside.add(domain)
    outside.add(x >= 100)
    outside.add(py_out != c_out)

    print()
    print("Outside region x >= 100:")
    print("mismatch query =", outside.check())

    if outside.check() == z3.sat:
        print(
            "Example mismatch:",
            outside.model()[x]
        )


check_pair(
    "TEST A: ORIGINAL PYTHON vs ORIGINAL C",
    "relational_poc/python_f.goto",
    "relational_poc/c_good_f.goto"
)

check_pair(
    "TEST B: ORIGINAL PYTHON vs INTENTIONALLY BAD C",
    "relational_poc/python_f.goto",
    "relational_poc/c_bad_f.goto"
)
