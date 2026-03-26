import os
import xbmc
import xbmcaddon
import xbmcgui

def run():
    addon = xbmcaddon.Addon()
    cwd = addon.getAddonInfo('path')
    process = os.path.join(cwd, 'resources', 'pm.pid')
    if os.path.exists(process):
        if xbmcgui.Dialog().yesno("Last.fm Playlist Generator", "Would you like to stop Last.fm Playlist Generator?"):
            os.remove(process)
            xbmc.log(msg="ADDON LFM: default os.remove", level=xbmc.LOGDEBUG)
    else:
        with open(process, 'w') as f:
            f.write(str(os.getpid()))
        from resources.lib import pm