"""Focused UNRUN tests for the consolidated ins-clock transport fix (v2).

Extracts the exact `def api` block from .github/workflows/clock.yml (embedded heredoc) and execs it
with inert globals (PAT, TASKS, os.environ, stubbed time.sleep, fake urlopen). No network, no credentials,
no workflow run. Covers: GET recover after RemoteDisconnected; GET recover when response.read() raises
IncompleteRead; GET recover after ConnectionResetError; GET exhaustion (3 attempts, rethrows); non-GET
single attempt; sentinel nondisclosure (evidence line carries class/method/attempt only, never exception text).
v3: namespace binds the http PACKAGE (not the http.client submodule) so http.client.* resolves exactly as
under the workflow's own "import http.client"; TASKS/PAT inert globals and no-raw-text diagnostic unchanged.
Sentinel coverage is bounded to the transient-retry evidence path; the tautological per-line newline
assertion was removed (it tested splitlines, not sanitization).
"""
import http.client
import io
import json
import os
import re
import types
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout

WORKFLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".github", "workflows", "clock.yml")
SENTINEL = "S3NTINEL-DO-NOT-LEAK-9f4b2c"


class _Resp:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._payload


class _BoomReadResp(_Resp):
    def read(self):
        raise http.client.IncompleteRead(b"")


def load_api_source(workflow_path):
    src = open(workflow_path, encoding="utf-8").read()
    m = re.search(r"python3 -u - <<'PY'\n(.*?)\n {10}PY", src, re.S)
    assert m, "embedded python block not found"
    dedented = "\n".join(l[10:] if l.startswith(" " * 10) else l for l in m.group(1).splitlines())
    fm = re.search(r"^def api\(.*?(?=^def |\Z)", dedented, re.S | re.M)
    assert fm, "def api block not found"
    return fm.group(0)


def build_api(fake_urlopen):
    ns = {
        "os": types.SimpleNamespace(environ={"PAT": "test-pat", "ISSUES_PAT": "test-issues-pat"}),
        "json": json,
        "time": types.SimpleNamespace(sleep=lambda s: None),
        "urllib": types.SimpleNamespace(
            request=types.SimpleNamespace(Request=urllib.request.Request, urlopen=fake_urlopen),
            error=urllib.error,
        ),
        "http": http,  # the package: api references http.client.*; submodule import above sets the attribute
        "PAT": "test-pat",
        "TASKS": "ins-labs/ins-clock-tasks",
    }
    exec(compile(load_api_source(WORKFLOW), "api_block", "exec"), ns)
    return ns["api"]


class ClockTransportRetryTests(unittest.TestCase):
    def test_get_recovers_after_remote_disconnected(self):
        calls = []

        def fake(req, timeout):
            calls.append(req.get_method())
            if len(calls) == 1:
                raise http.client.RemoteDisconnected("Remote end closed connection without response")
            return _Resp(200, b'{"ok": true}')

        api = build_api(fake)
        out = io.StringIO()
        with redirect_stdout(out):
            st, body = api("GET", "/repos/x/y")
        self.assertEqual(st, 200)
        self.assertEqual(body, {"ok": True})
        self.assertEqual(len(calls), 2)
        self.assertIn("RemoteDisconnected", out.getvalue())
        self.assertIn("attempt 1 of 3", out.getvalue())

    def test_get_recovers_after_incomplete_read_on_response_read(self):
        calls = []

        def fake(req, timeout):
            calls.append(req.get_method())
            if len(calls) == 1:
                return _BoomReadResp(200, b"")
            return _Resp(200, b'{"ok": true}')

        api = build_api(fake)
        out = io.StringIO()
        with redirect_stdout(out):
            st, body = api("GET", "/repos/x/y")
        self.assertEqual(st, 200)
        self.assertEqual(len(calls), 2)
        self.assertIn("IncompleteRead", out.getvalue())

    def test_get_recovers_after_connection_reset(self):
        calls = []

        def fake(req, timeout):
            calls.append(req.get_method())
            if len(calls) <= 2:
                raise ConnectionResetError("reset by peer")
            return _Resp(200, b"{}")

        api = build_api(fake)
        with redirect_stdout(io.StringIO()):
            st, _ = api("GET", "/repos/x/y")
        self.assertEqual(st, 200)
        self.assertEqual(len(calls), 3)

    def test_get_exhausts_and_rethrows(self):
        calls = []

        def fake(req, timeout):
            calls.append(req.get_method())
            raise http.client.BadStatusLine("garbage")

        api = build_api(fake)
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(http.client.BadStatusLine):
            api("GET", "/repos/x/y")
        self.assertEqual(len(calls), 3)
        self.assertIn("attempt 3 of 3", out.getvalue())

    def test_write_single_attempt_no_retry(self):
        calls = []

        def fake(req, timeout):
            calls.append(req.get_method())
            raise http.client.RemoteDisconnected("closed")

        api = build_api(fake)
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(http.client.RemoteDisconnected):
            api("POST", "/repos/x/y/issues", {"title": "t"})
        self.assertEqual(len(calls), 1)

    def test_evidence_line_discloses_no_exception_text(self):
        calls = []

        def fake(req, timeout):
            calls.append(req.get_method())
            if len(calls) == 1:
                raise http.client.RemoteDisconnected("reason=" + SENTINEL + " path=/secret?token=" + SENTINEL)
            return _Resp(200, b"{}")

        api = build_api(fake)
        out = io.StringIO()
        with redirect_stdout(out):
            st, _ = api("GET", "/repos/x/y")
        self.assertEqual(st, 200)
        text = out.getvalue()
        self.assertNotIn(SENTINEL, text)
        self.assertNotIn("/secret", text)
        self.assertIn("RemoteDisconnected", text)


if __name__ == "__main__":
    unittest.main()
