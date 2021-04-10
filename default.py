

import os
import time 
import xbmc
import xbmcgui
import xbmcaddon
from traceback import print_exc

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path')
BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )
process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")

def log(txt):
    #message = u'%s: %s' % ("LPM", txt)
    message = '%s: %s' % ("LPM", txt)
    xbmc.log(msg=message, level=xbmc.LOGERROR)

if os.path.exists(process):
    if xbmcgui.Dialog().yesno("Last.FM playlist generator (partymode)", "Would you like to exit partymode?" ):
        os.remove(process)        
        log("default os.remove")
else:
    open ( process , "w" ).write( "running" )
    import pm
    #xbmc.executebuiltin('XBMC.RunScript(%s)' % os.path.join( __cwd__, "pm.py" ))
