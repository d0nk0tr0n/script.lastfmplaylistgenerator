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
        if xbmcgui.Dialog().yesno("last.fm playlist generator", "Would you like to stop last.fm playlist generator?"):
            os.remove(process)
            log("default os.remove")
    else:
        with open(process, 'w') as f:
            f.write(str(os.getpid()))
        import pm
