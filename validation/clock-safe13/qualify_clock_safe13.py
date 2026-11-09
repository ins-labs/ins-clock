"""Clock safe13 native entry SOURCE ONLY; execute only on separately admitted host.

No production module import, workflow execution, tick, registry request, dispatch,
secret lookup, package installation or test discovery outside the exact class.
"""
import ast
import hashlib
import json
import pathlib
import runpy
import sys
import unittest

EXPECTED = (
    "test_generic_message_never_printed",
    "test_allowlisted_type_name_printed",
    "test_http_error_status_without_url",
    "test_malicious_class_name_is_replaced",
    "test_unknown_stage_is_unknown",
    "test_attached_status_appears",
    "test_non_int_status_is_na",
    "test_bool_status_is_na",
    "test_raising_status_property_is_na_without_traceback",
    "test_int_subclass_hostile_formatting_cannot_leak_or_raise",
    "test_hostile_str_subclass_stage_is_unknown",
    "test_hostile_metaclass_name_cannot_raise",
    "test_hostile_http_error_code_cannot_leak",
)
INPUTS = {
    ".github/workflows/clock.yml": "9e891a743c549a0d6e7f5d0bff962b7eab4748410cde376618105de0bb8ab015",
    "tests/tests/test_registry_failure_line.py": "6f5a969420450519f341401672e63fc7e06a9c8077c3bcf0889c44c9e5e67597",
}


def reject(code):
    print("CLOCK_SAFE13_ENTRY_REJECTED=" + code, file=sys.stderr)
    raise SystemExit(2)


def main():
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        reject("isolated_no_bytecode_required")
    if sys.implementation.name != "cpython" or tuple(sys.version_info[:3]) != (3, 12, 13):
        reject("exact_cpython_3_12_13_required")
    root = pathlib.Path(__file__).resolve().parent
    # Original test uses relative workflow path. Do not chdir into an unknown
    # repo or resolve production source outside this exact minimal packet.
    if pathlib.Path.cwd().resolve() != root:
        reject("packet_root_cwd_required")
    for name, wanted in INPUTS.items():
        target = root / name
        if target.is_symlink() or not target.is_file():
            reject("input_missing_or_symlink")
        if hashlib.sha256(target.read_bytes()).hexdigest() != wanted:
            reject("input_digest_mismatch")
    workflow = (root / ".github/workflows/clock.yml").read_text()
    start = "python3 -u - <<'PY'\n"
    end = "\n          PY"
    if workflow.count(start) != 1 or workflow.count(end) != 1:
        reject("workflow_boundary_mismatch")
    code = workflow.split(start, 1)[1].split(end, 1)[0]
    code = "\n".join(line[10:] for line in code.splitlines())
    # PARSE ONLY on the designated native host, never exec the workflow body.
    tree = ast.parse(code)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "registry_failure_line":
            selected.append(node.name)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"KNOWN_STAGES", "KNOWN_ERROR_TYPES"}:
                    selected.append(target.id)
    if sorted(selected) != ["KNOWN_ERROR_TYPES", "KNOWN_STAGES", "registry_failure_line"]:
        reject("helper_selection_mismatch")
    # This exact hash-pinned test's top level imports only Python stdlib,
    # parses workflow text, and defines a class. Its __main__ block is disabled.
    # Each of its13 tests execs ONLY the helper and two whitelist constants.
    namespace = runpy.run_path(str(root / "tests/tests/test_registry_failure_line.py"), run_name="clock_safe13_test_source")
    case = namespace.get("FailureLineTests")
    if not isinstance(case, type) or not issubclass(case, unittest.TestCase):
        reject("exact_test_class_missing")
    loader = unittest.TestLoader()
    if sorted(loader.getTestCaseNames(case)) != sorted(EXPECTED):
        reject("exact_test_names_mismatch")
    suite = unittest.TestSuite(case(name) for name in EXPECTED)
    if suite.countTestCases() != 13:
        reject("exact_test_count_mismatch")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    qualified = result.wasSuccessful() and result.testsRun == 13 and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses
    print("CLOCK_SAFE13_RESULT=" + json.dumps({
        "qualified": qualified,
        "python_version": sys.version,
        "python_executable": sys.executable,
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "source_commit": "9a3fb516917a7f033b91db71a9f28c31bd813219",
        "workflow_sha256": INPUTS[".github/workflows/clock.yml"],
        "test_sha256": INPUTS["tests/tests/test_registry_failure_line.py"],
    }, sort_keys=True))
    raise SystemExit(0 if qualified else 1)


if __name__ == "__main__":
    main()
