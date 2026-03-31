#!/usr/bin/env python3
import os 
import xbmc
import xbmcgui
import xbmcaddon
from traceback import print_exc

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path')
BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )
process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")

if os.path.exists(process):
    if xbmcgui.Dialog().yesno("Last.FM playlist generator", "Would you like to stop Last.FM playlist generator?" ):
        os.remove(process)        
else:
    with open(process, "w") as f:
        f.write(str(os.getpid()))
    import pm