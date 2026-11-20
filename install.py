#!/usr/bin/python3
"""Install/uninstall only this plugin, preserving other bar modules and config."""
from pathlib import Path
import datetime,json,shutil,subprocess,sys
PLUGIN='ciro.youtube-music'
home=Path.home();source=Path(__file__).resolve().parent;dest=home/'.config/omarchy/plugins'/PLUGIN;config=home/'.config/omarchy/shell.json'
remove='--remove' in sys.argv
if not config.exists():sys.exit('Se necesita Omarchy con ~/.config/omarchy/shell.json.')
if not remove:
    missing=[x for x in ('mpv','yt-dlp','python3') if not shutil.which(x)]
    if missing:sys.exit('Faltan dependencias. Ejecuta: omarchy pkg add mpv yt-dlp')
if remove and (dest/'backend/music.py').exists():subprocess.run([sys.executable,str(dest/'backend/music.py'),'request','{"action":"shutdown"}'],capture_output=True)
backup=config.with_name('shell.json.before-music-bar-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));shutil.copy2(config,backup)
data=json.loads(config.read_text());layout=data.setdefault('bar',{}).setdefault('layout',{})
for section,items in layout.items():
    if isinstance(items,list):layout[section]=[x for x in items if x.get('id')!=PLUGIN]
if not remove:
    if dest.exists():
        archive=home/'.local/state/omarchy/plugin-backups'/('music-bar-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        archive.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(dest,archive)
    dest.mkdir(parents=True,exist_ok=True)
    for name in ('BarWidget.qml','youtube-music.svg','manifest.json','LICENSE','README.md','backend','i18n','install.py'):
        item=source/name
        if item.is_dir():shutil.copytree(item,dest/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
        else:shutil.copy2(item,dest/name)
    items=layout.setdefault('centerEnd',[]);pos=next((i+1 for i,x in enumerate(items) if x.get('id')=='omarchy.weather'),len(items));items.insert(pos,{'id':PLUGIN})
    # Retire only the previous bridge created by this project, without changing Chrome policy.
    host=home/'.config/google-chrome/NativeMessagingHosts/com.omarchy.youtube_music.json'
    if host.exists():
        try:
            old=json.loads(host.read_text())
            if old.get('path')==str(dest/'bridge/bridge.py'):host.rename(host.with_suffix('.json.disabled-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))
        except (ValueError,OSError):pass
else:
    if dest.exists():
        archive=home/'.local/state/omarchy/plugin-backups'/('music-bar-removed-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));archive.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(dest),str(archive))
tmp=config.with_suffix('.music-bar.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(config)
print('Desinstalado.' if remove else 'Instalado junto al clima. Haz clic en el icono para buscar música.')
print('Copia de configuración:',backup)
