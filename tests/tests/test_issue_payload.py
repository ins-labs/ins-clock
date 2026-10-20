import ast, pathlib, unittest, datetime as dt
from zoneinfo import ZoneInfo

source = pathlib.Path('.github/workflows/clock.yml').read_text()
code = source.split("python3 -u - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
code = '\n'.join(l[10:] for l in code.splitlines())
tree = ast.parse(code)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'issue_payload')
labels_assign = next(n for n in tree.body if isinstance(n, ast.Assign)
                     and any(getattr(t, 'id', None) == 'CODE_LABELS' for t in n.targets))
MODULE = [labels_assign, fn]


class IssuePayloadTests(unittest.TestCase):
    def build(self, t, nxt, code_suffix, value='BODY'):
        ns = {'dt': dt, 'ZoneInfo': ZoneInfo,
              'CAI': ZoneInfo('Africa/Cairo'), 'ASSIGNEE': 'ins-sherbeeny'}
        exec(compile(ast.Module(body=MODULE, type_ignores=[]), '<issue_payload>', 'exec'), ns)
        return ns['issue_payload']('T%s__P6HL__000002_%s' % (t.strftime('%Y%m%d_%H%M'), code_suffix),
                                   t, nxt, value, '000002_' + code_suffix)

    def test_due_first_line_is_cairo_date(self):
        # 2026-10-20 01:30 UTC = 04:30 Cairo (EEST) -> Due 2026-10-20
        t = dt.datetime(2026, 10, 20, 1, 30, tzinfo=dt.timezone.utc)
        p = self.build(t, None, 'ELEC')
        self.assertTrue(p['body'].startswith('Due: 2026-10-20\n'), p['body'][:40])
        self.assertIn('BODY', p['body'])

    def test_due_rolls_to_next_cairo_day(self):
        # 2026-10-20 22:30 UTC = 2026-10-21 01:30 Cairo -> Due 2026-10-21
        t = dt.datetime(2026, 10, 20, 22, 30, tzinfo=dt.timezone.utc)
        p = self.build(t, None, 'ELEC')
        self.assertTrue(p['body'].startswith('Due: 2026-10-21\n'), p['body'][:40])

    def test_elec_labeled_karim(self):
        t = dt.datetime(2026, 10, 20, 3, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(self.build(t, None, 'ELEC')['labels'], ['agent:karim'])

    def test_unknown_code_unlabeled(self):
        t = dt.datetime(2026, 10, 20, 3, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(self.build(t, None, 'SOMETHING')['labels'], [])

    def test_assignee_preserved(self):
        t = dt.datetime(2026, 10, 20, 3, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(self.build(t, None, 'ELEC')['assignees'], ['ins-sherbeeny'])


if __name__ == '__main__':
    unittest.main()
