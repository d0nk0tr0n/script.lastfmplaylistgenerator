"""
    Script for generating smart playlists based on a seeding track and last.fm api
    Created by: ErlendSB
    Ported to python3 by d0nk0tr0n
"""
import os
import random
import time
import threading
import urllib.request
import urllib.parse
import re
import json as simplejson
from os.path import exists
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

__settings__ = xbmcaddon.Addon(id='script.lastfmplaylistgeneratorPM')
__cwd__      = __settings__.getAddonInfo('path')

def log(txt):
    message = '%s: %s' % ("LPM", txt)
    xbmc.log(msg=message, level=xbmc.LOGWARNING)

class MyPlayer( xbmc.Player ) :
    countFoundTracks = 0
    addedTracks = []
    firstRun = 0
    SCRIPT_NAME = "LAST.FM Playlist Generator"

    allowtrackrepeat =  __settings__.getSetting( "allowtrackrepeat" )
    preferdifferentartist = __settings__.getSetting( "preferdifferentartist" )
    numberoftrackstoadd = ( 1, 2, 3, 5, 10, )[ int( __settings__.getSetting( "numberoftrackstoadd" ) ) ]
    delaybeforesearching= ( 2, 5, 10, 30, )[ int( __settings__.getSetting( "delaybeforesearching" ) ) ]
    limitlastfmresult= ( 50, 100, 250, )[ int( __settings__.getSetting( "limitlastfmresult" ) ) ]
    minimalplaycount= ( 50, 100, 250, 500, )[ int( __settings__.getSetting( "minimalplaycount" ) ) ]
    minimalmatching= ( 1, 2, 5, 10, 20, )[ int( __settings__.getSetting( "minimalmatching" ) ) ]
    mode= ( "Similar tracks", "Top tracks of similar artist", "Custom", )[ int(__settings__.getSetting( "mode" ) ) ]
    timer = None

    apiPath = "http://ws.audioscrobbler.com/2.0/?api_key=3ae834eee073c460a250ee08979184ec"

    def __init__ ( self ):
        log("__init__ started")
        xbmc.Player.__init__( self )
        xbmc.PlayList(0).clear()
        self.firstRun = 1
        BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )
        process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")
        removeauto('lastfmplaylistgeneratorpm')
        addauto("if os.path.exists('" + os.path.normpath(process).replace('\\','\\\\') + "'):#lastfmplaylistgeneratorpm\n\tos.remove('" + os.path.normpath(process).replace('\\','\\\\') + "')","lastfmplaylistgeneratorpm")
        xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME+",Start by playing a song)")
        log("__init__ completed")

    def startPlayBack(self):
        log("[LFM PLG(PM)] startPlayBack started")
        if xbmc.Player().isPlayingAudio():
            currentlyPlayingTitle = xbmc.Player().getMusicInfoTag().getTitle()
            currentlyPlayingArtist = xbmc.Player().getMusicInfoTag().getArtist()
            log("[LFM PLG(PM)] " + currentlyPlayingArtist + " - " + currentlyPlayingTitle + " started playing")
            self.countFoundTracks = 0
            if (self.firstRun == 1):
                self.firstRun = 0
                album = xbmc.Player().getMusicInfoTag().getAlbum()
                log("[LFM PLG(PM)] Playing file: %s" % xbmc.Player().getMusicInfoTag().getURL())
                thumb = xbmc.getInfoLabel("Player.Art(thumb)")
                duration = xbmc.Player().getMusicInfoTag().getDuration()
                year = xbmc.Player().getMusicInfoTag().getYear()
                genre = xbmc.Player().getMusicInfoTag().getGenre()
                fanart = xbmc.getInfoLabel("Player.Art(fanart)")
                listitem = self.getListItem(currentlyPlayingTitle,currentlyPlayingArtist,album,thumb,fanart,duration,year,genre)
                xbmc.PlayList(0).clear()
                xbmc.executebuiltin('XBMC.ActivateWindow(10500)')
                xbmc.PlayList(0).add(url= xbmc.Player().getMusicInfoTag().getURL(), listitem = listitem)
                self.addedTracks += [xbmc.Player().getMusicInfoTag().getURL()]
            log("main_similarTracks stopping next")
            self.main_similarTracks(currentlyPlayingTitle,currentlyPlayingArtist)

    def onPlayBackStarted(self):
        log("[LFM PLG(PM)] onPlayBackStarted waiting:  " + str(self.delaybeforesearching) +" seconds")
        if (self.timer is not None and self.timer.is_alive()):
            self.timer.cancel()

        self.timer = threading.Timer(self.delaybeforesearching,self.startPlayBack)
        self.timer.start()

    def fetch_similarArtists( self, currentlyPlayingArtist ):
        apiMethod = "&method=artist.getsimilar&limit=50"

        Base_URL = self.apiPath + apiMethod + "&artist=" + urllib.parse.quote_plus(currentlyPlayingArtist)
        WebSock = urllib.request.urlopen(Base_URL)
        log("[LFM PLG(PM)] Request : " + Base_URL)
        WebHTML = WebSock.read().decode('utf-8')
        WebSock.close()

        similarArtists = re.findall("<artist>.*?<name>(.+?)</name>.*?<mbid>(.+?)</mbid>.*?<match>(.+?)</match>.*?</artist>", WebHTML, re.DOTALL )
        similarArtists = [x for x in similarArtists if float(x[2]) > (float(self.minimalmatching)/100.0)]
        return similarArtists

    def find_Artist(self, artistName):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": { "filter": {"field":"artist","operator":"is","value":"%s"} }, "id": 1}' % (artistName))
        json_response = simplejson.loads(json_query)
        if 'result' in json_response and json_response['result'] != None and 'artists' in json_response['result'] :
            return True
        return False

    def fetch_topTracksOfArtist( self, mbIdArtist ):
        apiMethod = "&method=artist.gettoptracks&limit=20"

        Base_URL = self.apiPath + apiMethod + "&mbid=" + urllib.parse.quote_plus(mbIdArtist)
        WebSock = urllib.request.urlopen(Base_URL)
        log("[LFM PLG(PM)] Request : " + Base_URL)
        WebHTML2 = WebSock.read().decode('utf-8')
        WebSock.close()
        topTracks = re.findall("<track rank=.+?>.*?<name>(.+?)</name>.*?<playcount>(.+?)</playcount>.*?<listeners>(.+?)</listeners>.*?<artist>.*?<name>(.+?)</name>.*?</artist>.*?</track>", WebHTML2, re.DOTALL )
        log("[LFM PLG(PM)] Count: " + str(len(topTracks)))
        topTracks = [x for x in topTracks if int(x[1]) > self.minimalplaycount]
        return topTracks

    def fetch_similarTracks( self, currentlyPlayingTitle, currentlyPlayingArtist ):
        apiMethod = "&method=track.getsimilar&limit=" + str(self.limitlastfmresult)

        Base_URL = self.apiPath + apiMethod + "&artist=" + urllib.parse.quote_plus(currentlyPlayingArtist) + "&track=" + urllib.parse.quote_plus(currentlyPlayingTitle)
        WebSock = urllib.request.urlopen(Base_URL)
        log("[LFM PLG(PM)] Request : " + Base_URL)
        WebHTML = WebSock.read().decode('utf-8')
        WebSock.close()

        similarTracks = re.findall("<track>.*?<name>(.+?)</name>.*?<playcount>(.+?)</playcount>.*?<match>(.+?)</match>.*?<artist>.*?<name>(.+?)</name>.*?</artist>.*?</track>", WebHTML, re.DOTALL )
        similarTracks = [x for x in similarTracks if int(x[1]) > self.minimalplaycount]
        similarTracks = [x for x in similarTracks if float(x[2]) > (float(self.minimalmatching)/100.0)]
        return similarTracks

    def main_similarTracks( self, currentlyPlayingTitle, currentlyPlayingArtist ):
        countTracks = 0
        similarTracks = []
        if(self.mode == "Similar tracks" or self.mode == "Custom"):
            similarTracks += self.fetch_similarTracks(currentlyPlayingTitle, currentlyPlayingArtist)
            countTracks = len(similarTracks)
        if(self.mode == "Top tracks of similar artist" or (self.mode == "Custom" and countTracks < 10)):
            similarArtists = self.fetch_similarArtists(currentlyPlayingArtist)
            log("[LFM PLG(PM)] Nb Similar Artists : " + str(len(similarArtists)))
            for similarArtistName, mbid, matchValue in similarArtists:
                if self.find_Artist(similarArtistName):
                    similarTracks += self.fetch_topTracksOfArtist(mbid)

        foundArtists = []
        countTracks = len(similarTracks)
        log("[LFM PLG(PM)] Count: " + str(countTracks))

        random.shuffle(similarTracks)
        selectedArtist = []
        for similarTrackName, playCount, matchValue, similarArtistName in similarTracks:
            similarTrackName = similarTrackName.replace("+"," ").replace("("," ").replace(")"," ").replace("&quot","''").replace("&amp;","and")
            similarArtistName = similarArtistName.replace("+"," ").replace("("," ").replace(")"," ").replace("&quot","''").replace("&amp;","and")
            log("Looking for: " + similarTrackName + " - " + similarArtistName + " - " + matchValue + "/" + playCount)
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "properties": ["title", "artist", "album", "file", "thumbnail", "duration", "fanart", "year", "genre" ], "limits": {"end":1}, "sort": {"method":"random"}, "filter": { "and":[{"field":"title","operator":"is","value":"%s"},{"field":"artist","operator":"is","value":"%s"}] } }, "id": 1}' % (similarTrackName, similarArtistName))
            json_response = simplejson.loads(json_query)
            if not('result' in json_response) or json_response['result'] == None or not('songs' in json_response['result']):
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": { "properties": ["title", "artist", "album", "file", "thumbnail", "duration", "fanart", "year", "genre" ], "limits": {"end":1}, "sort": {"method":"random"}, "filter": { "and":[{"field":"title","operator":"contains","value":"%s"},{"field":"artist","operator":"contains","value":"%s"}] } }, "id": 1}' % (similarTrackName, similarArtistName))
                json_response = simplejson.loads(json_query)

            # separate the records
            if 'result' in json_response and json_response['result'] != None and 'songs' in json_response['result']:
                for item in json_response['result']['songs']:
                    artist = ""
                    if (len(item["artist"]) > 0):
                        artist = item["artist"][0]
                    trackTitle = item["title"]
                    album = item["album"]
                    trackPath = item["file"]
                    thumb = item["thumbnail"]
                    duration = int(item["duration"])
                    fanart = item["fanart"]
                    genre = item["genre"]
                    year = int(item["year"])
                    if(artist not in selectedArtist):
                        selectedArtist.append(artist)
                        log("[LFM PLG(PM)] Found: " + str(trackTitle) + " by: " + str(artist))
                        if ((self.allowtrackrepeat == "true" or self.allowtrackrepeat == 1) or (trackPath not in self.addedTracks)):
                            if ((self.preferdifferentartist != "true" and self.preferdifferentartist != 1) or (similarArtistName) not in foundArtists):
                                listitem = self.getListItem(trackTitle,artist,album,thumb,fanart,duration,year,genre)
                                xbmc.PlayList(0).add(url=trackPath, listitem=listitem)
                                log("[LFM PLG(PM)] Add track : " + str(trackTitle) + " by: " + str(artist))
                                self.addedTracks += [trackPath]
                                xbmc.executebuiltin("Container.Refresh")
                                self.countFoundTracks += 1
                                if (similarArtistName not in foundArtists):
                                    foundArtists += [similarArtistName]

                if (self.countFoundTracks >= self.numberoftrackstoadd):
                    break

        if (self.countFoundTracks == 0):
            time.sleep(3)
            log("[LFM PLG(PM)] None found")
            xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME+",No similar tracks were found)")
            return False

        xbmc.executebuiltin('SetCurrentPlaylist(0)')

    def getListItem(self, trackTitle, artist, album, thumb, fanart, duration, year, genre):
        log("getListItem started")
        listitem = xbmcgui.ListItem(trackTitle)
        if (fanart == ""):
            cache_name = xbmc.getCacheThumbName( str(artist) )
            fanart = "special://profile/thumbnails/Music/%s/%s" % ( "Fanart", cache_name, )
        listitem.setProperty('fanart_image',fanart)
        listitem.setInfo('music', { 'title': trackTitle, 'artist': artist, 'album': album, 'duration': duration, 'year': year, 'genre': genre, 'tracknumber': 0 })
        listitem.setArt({ 'thumb' : thumb, 'fanart' : fanart})
        log("[LFM PLG(PM)] Fanart:%s" % fanart)
        log("[LFM PLG(PM)] Thumb:%s" % thumb)
        return listitem

def addauto(newentry, scriptcode):
    log("addauto started")
    autoexecfile = xbmcvfs.translatePath('special://home/userdata/autoexec.py')
    if exists(autoexecfile):
        with open(autoexecfile) as fh:
            lines = fh.readlines()
        lines.append("import time" + "#" + scriptcode + "\n")
        lines.append("time.sleep(2)" + "#" + scriptcode + "\n")
        lines.append(newentry + "#" + scriptcode + "\n")
        with open(autoexecfile, "w") as f:
            if not "import xbmc\n" in lines:
                f.write("import xbmc" + "#" + scriptcode + "\n")
            if not "import os\n" in lines:
                f.write("import os" + "#" + scriptcode + "\n")
            f.writelines(lines)
    else:
        with open(autoexecfile, "w") as f:
            f.write("import time" + "#" + scriptcode + "\n")
            f.write("time.sleep(2)" + "#" + scriptcode + "\n")
            f.write("import os" + "#" + scriptcode + "\n")
            f.write("import xbmc" + "#" + scriptcode + "\n")
            f.write(newentry + "#" + scriptcode + "\n")

def removeauto(scriptcode):
    log("removeauto started")
    autoexecfile = xbmcvfs.translatePath('special://home/userdata/autoexec.py')
    if exists(autoexecfile):
        with open(autoexecfile) as fh:
            lines = [ line for line in fh if not line.strip().endswith("#" + scriptcode) ]
        with open(autoexecfile, "w") as f:
            f.writelines(lines)

BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )

process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")

p=MyPlayer()
while(1):
    if os.path.exists(process):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                os.remove(process)
                log("deleted pidfile")
            xbmc.sleep(500)
        else:
            break
