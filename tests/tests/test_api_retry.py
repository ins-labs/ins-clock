import ast,pathlib,unittest,urllib.error,unittest.mock as mock,json,os
source=pathlib.Path('.github/workflows/clock.yml').read_text();code=source.split("python3 -u - <<'PY'\n",1)[1].split('\n          PY',1)[0];code='\n'.join(l[10:] for l in code.splitlines());tree=ast.parse(code);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='api')
class Response:
 status=200
 def __enter__(self):return self
 def __exit__(self,*a):pass
 def read(self):return b'{}'
class RetryTests(unittest.TestCase):
 def call(self,method,effects):
  import urllib.request,time
  ns={'urllib':urllib,'json':json,'os':os,'PAT':'synthetic','TASKS':'synthetic/tasks','time':time}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'<api>','exec'),ns)
  with mock.patch('urllib.request.urlopen',side_effect=effects) as op,mock.patch('time.sleep') as sleep:
   result=ns['api'](method,'/repos/synthetic/clock/actions/variables',{} if method!='GET' else None);return result,op.call_count,sleep.call_count
 def err(self,code):return urllib.error.HTTPError('https://api.github.com',code,'synthetic',{},None)
 def test_get_recovers_502(self):self.assertEqual(self.call('GET',[self.err(502),Response()]),((200,{}),2,1))
 def test_get_exhaustion_is_failure(self):self.assertEqual(self.call('GET',[self.err(503)]*3),((503,None),3,2))
 def test_mutation_never_replayed(self):self.assertEqual(self.call('POST',[self.err(502)]),((502,None),1,0))
 def test_permission_not_retried(self):self.assertEqual(self.call('GET',[self.err(403)]),((403,None),1,0))
 def test_read_timeout_retries(self):self.assertEqual(self.call('GET',[TimeoutError('synthetic'),Response()]),((200,{}),2,1))
 def test_mutation_timeout_stays_unknown(self):
  with self.assertRaises(TimeoutError):self.call('PATCH',[TimeoutError('synthetic')])
if __name__=='__main__':unittest.main()
