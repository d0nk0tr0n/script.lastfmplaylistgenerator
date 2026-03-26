import os
import xbmcaddon
import xbmcgui

def log(*args):
    message = 'LPG: ' + ' '.join(str(a.decode('utf-8') if isinstance(a, bytes) else a) for a in args)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def run():
    addon = xbmcaddon.Addon()
    cwd = addon.getAddonInfo('path')
    process = os.path.join(cwd, 'resources', 'pm.pid')
    if os.path.exists(process):
        if xbmcgui.Dialog().yesno("Last.fm Playlist Generator", "Would you like to stop last.fm playlist generator?"):
            os.remove(process)
            log("default os.remove")
    else:
        with open(process, 'w') as f:
            f.write(str(os.getpid()))
        import pm
