import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('music',Path(__file__).parents[1]/'backend/music.py');music=importlib.util.module_from_spec(spec);spec.loader.exec_module(music)
class FakePlayer:
    proc=None
    def ensure(self):pass
    def command(self,*args):self.last=args
    def close(self):pass
class Checks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();music.STATE=Path(self.tmp.name);self.original=music.Player;music.Player=FakePlayer
        self.backend=music.Backend();self.extract=music.extract
    def tearDown(self):
        music.extract=self.extract;music.Player=self.original;self.backend.pool.shutdown();self.tmp.cleanup()
    def test_plain_text_and_art(self):
        item=music.track({'id':'sMcWOaJFuw0','title':'<img src="https://evil.test">','art':'https://evil.test/tracker'})
        self.assertEqual(item['title'],'<img src="https://evil.test">');self.assertEqual(item['art'],'')
        self.assertIsNone(music.track({'id':'--exec=bad'}))
    def test_search_and_stale_response(self):
        music.extract=lambda *a:{'entries':[{'id':'sMcWOaJFuw0','title':'Public song'}]}
        self.backend.search_id=2;self.backend.search('old',1);self.assertEqual(self.backend.state['results'],[])
        self.backend.search('new',2);self.assertEqual(self.backend.state['results'][0]['title'],'Public song')
    def test_error_is_visible(self):
        def fail(*a):raise RuntimeError('Service unavailable')
        music.extract=fail;self.backend.search('hello',0)
        self.assertEqual(self.backend.state['error'],'Service unavailable');self.assertFalse(self.backend.state['busy'])
    def test_no_untrusted_commands(self):
        with self.assertRaises(ValueError):self.backend.handle({'action':'exec','command':'evil'})
        with self.assertRaises(ValueError):self.backend.handle({'action':'play','id':'../../secret'})
        with self.assertRaises(ValueError):self.backend.handle({'action':'play','id':'sMcWOaJFuw0'})
    def test_audio_and_recent(self):
        item=music.track({'id':'sMcWOaJFuw0','title':'A & B'})
        music.extract=lambda *a:{'url':'https://r1---sn-test.googlevideo.com/videoplayback','duration':205}
        self.backend.play_id=1;self.backend.play(item,1)
        self.assertEqual(self.backend.state['player']['title'],'A & B');self.assertEqual(self.backend.state['recent'][0]['id'],item['id'])
        self.assertTrue((music.STATE/'recent.json').exists())
    def test_stream_origin_validation(self):
        item=music.track({'id':'sMcWOaJFuw0','title':'A'})
        music.extract=lambda *a:{'url':'file:///etc/passwd'}
        self.backend.play(item,0);self.assertIn('audio público',self.backend.state['error'])
        self.assertEqual(self.backend.state['recent'],[])
if __name__=='__main__':unittest.main()
