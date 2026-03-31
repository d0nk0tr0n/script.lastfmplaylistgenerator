#!/usr/bin/env python3
import os
import xbmcgui
import xbmcaddon

process = os.path.join(xbmcaddon.Addon().getAddonInfo('path'), "resources", "pm.pid")
if os.path.exists(process):
    if xbmcgui.Dialog().yesno("Last.FM playlist generator", "Would you like to stop Last.FM playlist generator?"):
        os.remove(process)
else:
    with open(process, "w") as f:
        f.write(str(os.getpid()))
    import pm
