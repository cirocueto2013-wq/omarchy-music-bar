#!/usr/bin/python3
"""Public YouTube search and local mpv audio. No browser, cookies or credentials."""
import concurrent.futures,fcntl,json,math,os,re,shutil,socket,socketserver,subprocess,sys,tempfile,threading,time
from pathlib import Path
STATE=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'omarchy/music-public'
RUNTIME=Path(os.environ.get('XDG_RUNTIME_DIR',f'/tmp/omarchy-music-{os.getuid()}'))/'omarchy-music-public'
VIDEO=re.compile(r'^[A-Za-z0-9_-]{11}$')

def prepare():
    for p in (STATE,RUNTIME):p.mkdir(parents=True,exist_ok=True,mode=0o700)
    if RUNTIME.stat().st_uid!=os.getuid() or RUNTIME.is_symlink():raise RuntimeError('Unsafe runtime directory')
    RUNTIME.chmod(0o700)

def write_json(path,data):
    fd,tmp=tempfile.mkstemp(prefix='.',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(data,f,ensure_ascii=False)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def track(item):
    ident=str(item.get('id',''))
    if not VIDEO.fullmatch(ident):return None
    thumbs=item.get('thumbnails') or []
    art=item.get('art') or (thumbs[-1].get('url','') if thumbs else '')
    if not re.match(r'^https://(?:[a-z0-9-]+\.)*(?:ytimg\.com|googleusercontent\.com|ggpht\.com)/',art):art=''
    return dict(id=ident,kind='song',title=str(item.get('title') or ident)[:300],subtitle=str(item.get('subtitle') or item.get('uploader') or item.get('channel') or '')[:300],art=art[:1500],duration=item.get('duration') or 0)

def read_volume():
    try:
        value=float(json.loads((STATE/'volume.json').read_text()).get('volume',70))
        return max(0,min(100,value)) if math.isfinite(value) else 70
    except (OSError,ValueError,TypeError,AttributeError):return 70

def set_volume(value):
    if isinstance(value,bool):raise ValueError('Invalid volume')
    number=float(value)
    if not math.isfinite(number):raise ValueError('Invalid volume')
    number=max(0,min(100,number))
    write_json(STATE/'volume.json',{'volume':number})
    try:Player().command('set_property','volume',number)
    except OSError:pass
    return {'ok':True,'volume':number}

def extract(query,search=True):
    tool=shutil.which('yt-dlp')
    if not tool:raise RuntimeError('Falta yt-dlp. Instala: omarchy pkg add mpv yt-dlp')
    args=[tool,'--ignore-config','--no-cache-dir','--socket-timeout','10','--retries','1','--extractor-retries','1','--dump-single-json']
    if search:args+=['--flat-playlist','--playlist-end','20','--', 'ytsearch20:'+query[:200]]
    else:
        if not VIDEO.fullmatch(query):raise ValueError('Invalid video ID')
        args+=['--no-playlist','-f','bestaudio/best','--','https://www.youtube.com/watch?v='+query]
    # Temporary output bounds memory use; authentication options are never passed.
    with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
        proc=subprocess.Popen(args,stdout=out,stderr=err)
        start=time.monotonic()
        while proc.poll() is None:
            if time.monotonic()-start>45 or out.tell()>12_000_000 or err.tell()>500_000:
                proc.kill();proc.wait();raise RuntimeError('La búsqueda o reproducción tardó demasiado. Intenta otra vez.')
            time.sleep(.1)
        if proc.returncode:
            err.seek(0);detail=err.read(20000).decode(errors='replace')
            if 'sign in' in detail.lower() or 'cookies' in detail.lower():raise RuntimeError('YouTube exige verificación para este contenido o conexión. No se usan cuentas ni cookies; prueba otra canción o vuelve a intentar más tarde.')
            raise RuntimeError('YouTube no respondió. Revisa tu conexión y actualiza yt-dlp con omarchy pkg add yt-dlp.')
        out.seek(0);return json.load(out)

class Player:
    def __init__(self):self.proc=None;self.serial=0;self.lock=threading.Lock();self.on_end=None;self.event_socket=None
    def ensure(self):
        if self.proc and self.proc.poll() is None:return
        if not shutil.which('mpv'):raise RuntimeError('Falta mpv. Instala: omarchy pkg add mpv yt-dlp')
        path=RUNTIME/'mpv.sock';path.unlink(missing_ok=True)
        self.proc=subprocess.Popen(['mpv','--no-config','--no-video','--idle=yes','--keep-open=no','--no-terminal','--ytdl=no','--input-ipc-server='+str(path)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(60):
            if path.exists():
                self.event_socket=socket.socket(socket.AF_UNIX);self.event_socket.connect(str(path))
                threading.Thread(target=self.events,daemon=True).start()
                self.command('set_property','volume',read_volume())
                return
            if self.proc.poll() is not None:break
            time.sleep(.05)
        raise RuntimeError('No se pudo iniciar mpv.')
    def events(self):
        try:
            f=self.event_socket.makefile('rb')
            for raw in f:
                if len(raw)>65536:continue
                event=json.loads(raw)
                if event.get('event')=='end-file' and self.on_end:self.on_end(event.get('reason'))
        except (OSError,ValueError):pass
    def command(self,*args):
        with self.lock:
            self.serial+=1
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(1);client.connect(str(RUNTIME/'mpv.sock'))
                client.sendall((json.dumps({'command':list(args),'request_id':self.serial})+'\n').encode())
                f=client.makefile('rb')
                for _ in range(20):
                    raw=f.readline(65536)
                    if not raw:break
                    response=json.loads(raw)
                    if response.get('request_id')==self.serial:return response.get('data')
        return None
    def get(self,name):return self.command('get_property',name)
    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()

class Backend:
    def __init__(self):
        self.lock=threading.RLock();self.player=Player();self.player.on_end=self.ended;self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.search_id=0;self.play_id=0;self.queue=[];self.index=0;self.was_active=False
        self.state=dict(connected=True,updated=int(time.time()),busy=False,error='',query='',results=[],recent=[],player={},loading=False)
        try:
            saved=json.loads((STATE/'recent.json').read_text())
            self.state['recent']=[t for x in saved[:40] if (t:=track(x))]
        except (OSError,ValueError,TypeError):pass
        missing=[x for x in ('mpv','yt-dlp') if not shutil.which(x)]
        if missing:self.state['error']='Faltan '+', '.join(missing)+'. Instala: omarchy pkg add mpv yt-dlp'
        self.publish()
    def publish(self):
        with self.lock:self.state['updated']=int(time.time());write_json(STATE/'state.json',self.state)
    def search(self,query,serial):
        try:
            data=extract(query)
            values=[t for item in (data.get('entries') or [])[:20] if item and (t:=track(item))]
            with self.lock:
                if serial!=self.search_id:return
                self.state['results']=values;self.state['error']='' if values else 'No se encontraron canciones.'
        except Exception as e:
            with self.lock:
                if serial==self.search_id:self.state['error']=str(e)[:500]
        finally:
            with self.lock:
                if serial==self.search_id:self.state['busy']=False
                self.publish()
    def play(self,item,serial):
        try:
            data=extract(item['id'],False);url=data.get('url','')
            if not re.match(r'^https://(?:[a-z0-9-]+\.)*googlevideo\.com/',url):raise RuntimeError('No se encontró un audio público reproducible.')
            with self.lock:
                if serial!=self.play_id:return
                self.player.ensure();self.player.command('loadfile',url,'replace');self.player.command('set_property','pause',False)
                self.was_active=False
                self.state['player']=dict(title=item['title'],artist=item['subtitle'],art=item['art'],playing=True,position=0,duration=data.get('duration') or item['duration'])
                self.state['recent']=[item]+[x for x in self.state['recent'] if x['id']!=item['id']][:39]
                write_json(STATE/'recent.json',self.state['recent']);self.state['error']=''
        except Exception as e:
            with self.lock:
                if serial==self.play_id:self.state['error']=str(e)[:500]
        finally:
            with self.lock:
                if serial==self.play_id:self.state['loading']=False
                self.publish()
    def start(self,item):
        self.play_id+=1;self.state['loading']=True;self.state['error']='';self.publish()
        self.pool.submit(self.play,item,self.play_id)
    def skip(self,step):
        n=self.index+step
        if 0<=n<len(self.queue):self.index=n;self.start(self.queue[n])
    def handle(self,data):
        if not isinstance(data,dict):raise ValueError('Invalid command')
        action=data.get('action')
        with self.lock:
            if action=='search':
                query=str(data.get('query','')).strip()[:200]
                if not query:raise ValueError('Escribe una búsqueda.')
                self.search_id+=1;self.state.update(query=query,busy=True,error='');self.pool.submit(self.search,query,self.search_id)
            elif action=='play':
                ident=str(data.get('id',''))
                if not VIDEO.fullmatch(ident):raise ValueError('Invalid video ID')
                results=self.state['results'];recent=self.state['recent']
                source=results if any(x['id']==ident for x in results) else recent
                item=next((x for x in source if x['id']==ident),None)
                if not item:raise ValueError('Busca la canción antes de reproducirla.')
                self.queue=list(source);self.index=next(i for i,x in enumerate(source) if x['id']==ident);self.start(item)
            elif action=='toggle':
                if self.player.proc and self.player.proc.poll() is None:self.player.command('cycle','pause')
            elif action=='next':self.skip(1)
            elif action=='previous':self.skip(-1)
            elif action=='stop':
                self.play_id+=1;self.state['loading']=False
                if self.player.proc and self.player.proc.poll() is None:self.player.command('stop')
                self.state['player']={};self.was_active=False
            elif action!='ensure':raise ValueError('Unknown action')
            self.publish();return {'ok':True}
    def ended(self,reason):
        with self.lock:
            if reason=='eof' and not self.state['loading']:
                self.state['player']['playing']=False;self.skip(1)
            elif reason=='error':
                self.state['error']='No se pudo reproducir el audio. Prueba otra canción o actualiza yt-dlp.'
                self.state['player']['playing']=False
            self.publish()
    def monitor(self):
        while True:
            time.sleep(1)
            with self.lock:
                if self.player.proc and self.player.proc.poll() is None and self.state['player']:
                    try:
                        idle=self.player.get('idle-active')
                        if idle is False:
                            self.was_active=True
                            self.state['player'].update(position=self.player.get('time-pos') or 0,duration=self.player.get('duration') or self.state['player'].get('duration',0),playing=not self.player.get('pause'))
                    except (OSError,ValueError):pass
                self.publish()

def serve():
    lock=open(RUNTIME/'daemon.lock','w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return
    path=RUNTIME/'control.sock';path.unlink(missing_ok=True);backend=Backend()
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(3)
            try:
                raw=self.rfile.readline(16385)
                if len(raw)>16384:raise ValueError('Command too large')
                data=json.loads(raw)
                if data.get('action')=='shutdown':
                    backend.play_id+=1
                    threading.Timer(.1,server.shutdown).start();response={'ok':True}
                else:response=backend.handle(data)
            except Exception as e:response={'ok':False,'error':str(e)[:500]}
            self.wfile.write((json.dumps(response)+'\n').encode())
    server=socketserver.ThreadingUnixStreamServer(str(path),Handler);os.chmod(path,0o600)
    threading.Thread(target=backend.monitor,daemon=True).start()
    try:server.serve_forever()
    finally:
        backend.player.close();backend.pool.shutdown(wait=False,cancel_futures=True);backend.state['connected']=False;backend.publish();server.server_close();path.unlink(missing_ok=True)

def request(data):
    if data.get('action')=='volume':return set_volume(data.get('value'))
    def call():
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(3);client.connect(str(RUNTIME/'control.sock'));client.sendall((json.dumps(data)+'\n').encode());return json.loads(client.makefile('rb').readline(16384))
    try:return call()
    except (OSError,ValueError):
        subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'serve'],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(40):
            time.sleep(.1)
            try:return call()
            except (OSError,ValueError):pass
        raise RuntimeError('No se pudo iniciar el servicio local.')

def main():
    prepare()
    if len(sys.argv)>1 and sys.argv[1]=='serve':serve()
    else:
        result=request(json.loads(sys.argv[2]) if len(sys.argv)>2 else {'action':'ensure'})
        print(json.dumps(result,ensure_ascii=False));return 0 if result.get('ok') else 1
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
