import ast,pathlib,unittest,urllib.error,json
source=pathlib.Path('.github/workflows/clock.yml').read_text();code=source.split("python3 -u - <<'PY'\n",1)[1].split('\n          PY',1)[0];code='\n'.join(l[10:] for l in code.splitlines());tree=ast.parse(code)
WANTED={'KNOWN_STAGES','KNOWN_ERROR_TYPES'}
nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name=='registry_failure_line') or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in WANTED for t in n.targets))]
SECRET='ghp_SYNTHETICTOKEN0123456789'
URL='https://api.example.test/x?token='+SECRET+'&q=1'
class FailureLineTests(unittest.TestCase):
 def line(self,stage,exc):
  ns={'urllib':urllib,'json':json}
  exec(compile(ast.Module(body=nodes,type_ignores=[]),'<helper>','exec'),ns)
  return ns['registry_failure_line'](stage,exc)
 def test_generic_message_never_printed(self):
  line=self.line('d1 select',Exception('boom '+SECRET+' '+URL))
  self.assertEqual(line,'registry sync failed: stage=d1 select type=UnexpectedError status=n/a')
  for bad in (SECRET,'boom','https','token=','q=1'):self.assertNotIn(bad,line)
 def test_allowlisted_type_name_printed(self):
  self.assertEqual(self.line('reconcile',RuntimeError('secret '+SECRET)),'registry sync failed: stage=reconcile type=RuntimeError status=n/a')
 def test_http_error_status_without_url(self):
  e=urllib.error.HTTPError(URL,502,'msg '+SECRET,{},None)
  line=self.line('backup write',e)
  self.assertEqual(line,'registry sync failed: stage=backup write type=HTTPError status=502')
  for bad in (SECRET,'https','token=','q=1','msg'):self.assertNotIn(bad,line)
 def test_malicious_class_name_is_replaced(self):
  cls=type('RuntimeError token='+SECRET,(Exception,),{})
  line=self.line('backup read',cls('x'))
  self.assertIn('type=UnexpectedError',line)
  self.assertNotIn(SECRET,line);self.assertNotIn('token=',line)
 def test_unknown_stage_is_unknown(self):
  line=self.line('stage '+SECRET,RuntimeError('x'))
  self.assertIn('stage=unknown',line);self.assertNotIn(SECRET,line)
 def test_attached_status_appears(self):
  e=RuntimeError('variable reload failed');e.status=403
  self.assertEqual(self.line('variable reload',e),'registry sync failed: stage=variable reload type=RuntimeError status=403')
 def test_non_int_status_is_na(self):
  e=RuntimeError('x');e.status=SECRET
  line=self.line('d1 select',e)
  self.assertIn('status=n/a',line);self.assertNotIn(SECRET,line)
 def test_bool_status_is_na(self):
  e=RuntimeError('x');e.status=True
  self.assertIn('status=n/a',self.line('d1 select',e))
 def test_raising_status_property_is_na_without_traceback(self):
  class Hostile(RuntimeError):
   @property
   def status(self):raise ValueError('leak '+SECRET)
  line=self.line('d1 select',Hostile('x'))
  self.assertEqual(line,'registry sync failed: stage=unknown type=UnexpectedError status=n/a')
  self.assertNotIn(SECRET,line)
 def test_int_subclass_hostile_formatting_cannot_leak_or_raise(self):
  class EvilInt(int):
   def __str__(self):return SECRET
   def __repr__(self):return SECRET
   def __format__(self,spec):return SECRET
   def __index__(self):raise ValueError(SECRET)
   def __int__(self):raise ValueError(SECRET)
  e=RuntimeError('x');e.status=EvilInt(500)
  line=self.line('d1 select',e)
  self.assertEqual(line,'registry sync failed: stage=d1 select type=RuntimeError status=n/a')
  self.assertNotIn(SECRET,line)
 def test_hostile_str_subclass_stage_is_unknown(self):
  class EvilStr(str):
   def __eq__(self,o):raise ValueError(SECRET)
   def __hash__(self):return 0
  line=self.line(EvilStr('d1 select'),RuntimeError('x'))
  self.assertIn('stage=unknown',line);self.assertNotIn(SECRET,line)
 def test_hostile_metaclass_name_cannot_raise(self):
  class Meta(type):
   @property
   def __name__(cls):raise ValueError(SECRET)
  cls=Meta('X',(Exception,),{})
  line=self.line('d1 select',cls('x'))
  self.assertEqual(line,'registry sync failed: stage=unknown type=UnexpectedError status=n/a')
  self.assertNotIn(SECRET,line)
 def test_hostile_http_error_code_cannot_leak(self):
  e=urllib.error.HTTPError(URL,502,'m',{},None);e.code=SECRET
  line=self.line('backup read',e)
  self.assertEqual(line,'registry sync failed: stage=backup read type=HTTPError status=n/a')
  self.assertNotIn(SECRET,line)
if __name__=='__main__':unittest.main()
