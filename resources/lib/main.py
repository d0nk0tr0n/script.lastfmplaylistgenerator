import os
import xbmcaddon
import xbmcgui

def log(msg):
    import xbmc
    xbmc.log(msg)

def run():
    addon = xbmcaddon.Addon()
    cwd = addon.getAddonInfo('path')
    process = os.path.join(cwd, 'resources', 'pm.pid')

    if os.path.exists(process):
        if xbmcgui.Dialog().yesno("Last.FM playlist generator", "Would you like to stop Last.FM playlist generator?"):
            os.remove(process)
            log("default os.remove")
    else:
        open(process, 'w').write(str(os.getpid()))
        import pm
