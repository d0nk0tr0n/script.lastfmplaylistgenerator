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
import html
import unicodedata
import json as simplejson
from os.path import exists
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

__settings__      = xbmcaddon.Addon(id='script.lastfmplaylistgeneratorPM')
__cwd__           = __settings__.getAddonInfo('path')
__addonversion__  = __settings__.getAddonInfo('version')

def log(txt):
    message = '%s: %s' % ("[ADDON LFM]", txt)
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
    minimalplaycount= ( 1000, 10000, 50000, 100000, 250000, 500000, 1000000, )[ int( __settings__.getSetting( "minimalplaycount" ) ) ]
    minimalmatching= ( 1, 2, 5, 10, 20, )[ int( __settings__.getSetting( "minimalmatching" ) ) ]
    mode= ( "Similar tracks", "Top tracks of similar artist", "Custom", )[ int(__settings__.getSetting( "mode" ) ) ]
    timer = None

    apiPath = "http://ws.audioscrobbler.com/2.0/?api_key=3ae834eee073c460a250ee08979184ec"

    def __init__ ( self ):
        log("__init__ started v" + __addonversion__)
        xbmc.Player.__init__( self )
        xbmc.PlayList(0).clear()
        self.firstRun = 1
        BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )
        process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")
        removeauto('lastfmplaylistgeneratorpm')
        addauto("if os.path.exists('" + os.path.normpath(process).replace('\\','\\\\') + "'):#lastfmplaylistgeneratorpm\n\tos.remove('" + os.path.normpath(process).replace('\\','\\\\') + "')","lastfmplaylistgeneratorpm")
        log("allowtrackrepeat=%r preferdifferentartist=%r numberoftrackstoadd=%r" % (self.allowtrackrepeat, self.preferdifferentartist, self.numberoftrackstoadd))
        xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME+",Start by playing a song)")
        log("__init__ completed")

    def startPlayBack(self):
        log("startPlayBack started")
        if xbmc.Player().isPlayingAudio():
            currentlyPlayingTitle = xbmc.Player().getMusicInfoTag().getTitle()
            currentlyPlayingArtist = xbmc.Player().getMusicInfoTag().getArtist()
            log(currentlyPlayingArtist + " - " + currentlyPlayingTitle + " started playing")
            self.countFoundTracks = 0
            if (self.firstRun == 1):
                self.firstRun = 0
                album = xbmc.Player().getMusicInfoTag().getAlbum()
                log("Playing file: %s" % xbmc.Player().getMusicInfoTag().getURL())
                thumb = xbmc.getInfoLabel("Player.Art(thumb)")
                duration = xbmc.Player().getMusicInfoTag().getDuration()
                year = xbmc.Player().getMusicInfoTag().getYear()
                genre = xbmc.Player().getMusicInfoTag().getGenre()
                fanart = xbmc.getInfoLabel("Player.Art(fanart)")
                listitem = self.getListItem(currentlyPlayingTitle,currentlyPlayingArtist,album,thumb,fanart,duration,year,genre)
                xbmc.PlayList(0).clear()
                xbmc.executebuiltin('XBMC.ActivateWindow(10500)')
                xbmc.PlayList(0).add(url= xbmc.Player().getMusicInfoTag().getURL(), listitem = listitem)
                xbmc.Player().updateInfoTag(listitem)
                self.addedTracks += [xbmc.Player().getMusicInfoTag().getURL()]
            log("main_similarTracks stopping next")
            self.main_similarTracks(currentlyPlayingTitle,currentlyPlayingArtist)

    def onPlayBackStarted(self):
        log("onPlayBackStarted waiting:  " + str(self.delaybeforesearching) +" seconds")
        if (self.timer is not None and self.timer.is_alive()):
            self.timer.cancel()

        self.timer = threading.Timer(self.delaybeforesearching,self.startPlayBack)
        self.timer.start()

    def fetch_similarArtists( self, currentlyPlayingArtist ):
        apiMethod = "&method=artist.getsimilar&limit=50&autocorrect=1"

        Base_URL = self.apiPath + apiMethod + "&artist=" + urllib.parse.quote_plus(currentlyPlayingArtist)
        WebSock = urllib.request.urlopen(Base_URL)
        log("Request : " + Base_URL)
        WebHTML = WebSock.read().decode('utf-8')
        WebSock.close()

        similarArtists = re.findall("<artist>.*?<name>(.+?)</name>.*?<mbid>(.*?)</mbid>.*?<match>(.+?)</match>.*?</artist>", WebHTML, re.DOTALL )
        similarArtists = [x for x in similarArtists if float(x[2]) > (float(self.minimalmatching)/100.0)]
        return similarArtists

    def find_Artist(self, artistName):
        json_query = xbmc.executeJSONRPC(simplejson.dumps({
            "jsonrpc": "2.0", "method": "AudioLibrary.GetArtists",
            "params": {"filter": {"field": "artist", "operator": "is", "value": artistName}},
            "id": 1}))
        json_response = simplejson.loads(json_query)
        if 'result' in json_response and json_response['result'] != None and 'artists' in json_response['result'] :
            return True
        return False

    def fetch_topTracksOfArtist( self, mbIdArtist ):
        apiMethod = "&method=artist.gettoptracks&limit=20"

        Base_URL = self.apiPath + apiMethod + "&mbid=" + urllib.parse.quote_plus(mbIdArtist)
        WebSock = urllib.request.urlopen(Base_URL)
        log("Request : " + Base_URL)
        WebHTML2 = WebSock.read().decode('utf-8')
        WebSock.close()
        topTracks = re.findall("<track rank=.+?>.*?<name>(.+?)</name>.*?<playcount>(.+?)</playcount>.*?<listeners>(.+?)</listeners>.*?<artist>.*?<name>(.+?)</name>.*?</artist>.*?</track>", WebHTML2, re.DOTALL )
        log("Count: " + str(len(topTracks)))
        topTracks = [x for x in topTracks if int(x[1]) > self.minimalplaycount]
        topTracks.sort(key=lambda x: int(x[2]), reverse=True)
        return topTracks

    def fetch_similarTracks( self, currentlyPlayingTitle, currentlyPlayingArtist ):
        apiMethod = "&method=track.getsimilar&limit=" + str(self.limitlastfmresult) + "&autocorrect=1"

        Base_URL = self.apiPath + apiMethod + "&artist=" + urllib.parse.quote_plus(currentlyPlayingArtist) + "&track=" + urllib.parse.quote_plus(currentlyPlayingTitle)
        WebSock = urllib.request.urlopen(Base_URL)
        log("Request : " + Base_URL)
        WebHTML = WebSock.read().decode('utf-8')
        WebSock.close()

        similarTracks = re.findall("<track>.*?<name>(.+?)</name>.*?<playcount>(.+?)</playcount>.*?<match>(.+?)</match>.*?<artist>.*?<name>(.+?)</name>.*?</artist>.*?</track>", WebHTML, re.DOTALL )
        similarTracks = [x for x in similarTracks if int(x[1]) > self.minimalplaycount]
        similarTracks = [x for x in similarTracks if float(x[2]) > (float(self.minimalmatching)/100.0)]
        return similarTracks

    def normalize_for_search(self, text):
        text = html.unescape(text)
        # Normalize smart quotes to straight quotes
        text = text.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
        # Normalize fancy dashes to hyphens
        text = text.replace('\u2010', '-').replace('\u2011', '-').replace('\u2012', '-').replace('\u2013', '-').replace('\u2014', '-')
        # Strip diacritics
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text

    def clean_title_for_search(self, title):
        title = self.normalize_for_search(title)
        # Strip live/remaster suffixes that Last.fm doesn't index
        title = re.sub(r'\s*[\(\[]\s*(live[^\)\]]*|remaster(?:ed)?[^\)\]]*|\d{4}\s*remaster(?:ed)?)\s*[\)\]]', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-\s*(remaster(?:ed)?(\s+\d{4})?|\d{4}\s+remaster(?:ed)?)$', '', title, flags=re.IGNORECASE)
        # Strip featuring suffixes that Last.fm doesn't include in track titles
        title = re.sub(r'\s*[\(\[]\s*(?:featuring|feat\.?|ft\.?)\s+[^\)\]]+[\)\]]', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-\s*(?:featuring|feat\.?|ft\.?)\s+.+$', '', title, flags=re.IGNORECASE)
        return title.strip()

    def main_similarTracks( self, currentlyPlayingTitle, currentlyPlayingArtist ):
        searchTitle = self.clean_title_for_search(currentlyPlayingTitle)
        if searchTitle != currentlyPlayingTitle:
            log("Cleaned title for search: " + searchTitle)
        countTracks = 0
        similarTracks = []
        if(self.mode == "Similar tracks" or self.mode == "Custom"):
            similarTracks += self.fetch_similarTracks(searchTitle, currentlyPlayingArtist)
            countTracks = len(similarTracks)
        if(self.mode == "Top tracks of similar artist" or (self.mode == "Custom" and countTracks < 10)):
            similarArtists = self.fetch_similarArtists(currentlyPlayingArtist)
            log("Nb Similar Artists : " + str(len(similarArtists)))
            artistFetchCount = 0
            for similarArtistName, mbid, matchValue in similarArtists:
                if artistFetchCount >= 5:
                    log("Reached similar artist fetch cap")
                    break
                if not mbid:
                    log("Skipping " + similarArtistName + " - no mbid")
                    continue
                if self.find_Artist(self.normalize_for_search(similarArtistName)):
                    similarTracks += self.fetch_topTracksOfArtist(mbid)
                    artistFetchCount += 1

        foundArtists = []
        countTracks = len(similarTracks)
        log("Count: " + str(countTracks))

        random.shuffle(similarTracks)
        selectedArtist = []
        artistExistsCache = {}
        for similarTrackName, playCount, matchValue, similarArtistName in similarTracks:
            similarTrackName = html.unescape(similarTrackName)
            similarArtistName = html.unescape(similarArtistName)
            searchTrackName = self.clean_title_for_search(similarTrackName)
            searchArtistName = self.normalize_for_search(similarArtistName)
            if searchArtistName not in artistExistsCache:
                artistExistsCache[searchArtistName] = self.find_Artist(searchArtistName)
            if not artistExistsCache[searchArtistName]:
                log("Artist not in library, skipping: " + searchArtistName)
                continue
            if searchTrackName != similarTrackName:
                log("Cleaned similar track title for search: " + searchTrackName)
            log("Looking for: " + similarTrackName + " - " + similarArtistName + " - " + playCount + "/" + matchValue)
            props = ["title", "artist", "album", "file", "thumbnail", "duration", "fanart", "year", "genre"]
            json_query = xbmc.executeJSONRPC(simplejson.dumps({
                "jsonrpc": "2.0", "method": "AudioLibrary.GetSongs",
                "params": {"properties": props, "limits": {"end": 1}, "sort": {"method": "random"},
                           "filter": {"and": [{"field": "title", "operator": "is", "value": searchTrackName},
                                              {"field": "artist", "operator": "is", "value": searchArtistName}]}},
                "id": 1}))
            json_response = simplejson.loads(json_query)
            if not('result' in json_response) or json_response['result'] == None or not('songs' in json_response['result']):
                json_query = xbmc.executeJSONRPC(simplejson.dumps({
                    "jsonrpc": "2.0", "method": "AudioLibrary.GetSongs",
                    "params": {"properties": props, "limits": {"end": 1}, "sort": {"method": "random"},
                               "filter": {"and": [{"field": "title", "operator": "contains", "value": searchTrackName},
                                                  {"field": "artist", "operator": "contains", "value": searchArtistName}]}},
                    "id": 1}))
                json_response = simplejson.loads(json_query)
            if not('result' in json_response) or json_response['result'] == None or not('songs' in json_response['result']):
                json_query = xbmc.executeJSONRPC(simplejson.dumps({
                    "jsonrpc": "2.0", "method": "AudioLibrary.GetSongs",
                    "params": {"properties": props, "limits": {"end": 1}, "sort": {"method": "random"},
                               "filter": {"and": [{"field": "title", "operator": "contains", "value": similarTrackName},
                                                  {"field": "artist", "operator": "contains", "value": similarArtistName}]}},
                    "id": 1}))
                json_response = simplejson.loads(json_query)
            if not('result' in json_response) or json_response['result'] == None or not('songs' in json_response['result']):
                if any(c in searchTrackName + searchArtistName for c in ("'", '"', '-')):
                    smartTrackName = searchTrackName.replace("'", "\u2019").replace('"', "\u201d").replace('-', "\u2010")
                    smartArtistName = searchArtistName.replace("'", "\u2019").replace('"', "\u201d").replace('-', "\u2010")
                    json_query = xbmc.executeJSONRPC(simplejson.dumps({
                        "jsonrpc": "2.0", "method": "AudioLibrary.GetSongs",
                        "params": {"properties": props, "limits": {"end": 1}, "sort": {"method": "random"},
                                   "filter": {"and": [{"field": "title", "operator": "contains", "value": smartTrackName},
                                                      {"field": "artist", "operator": "contains", "value": smartArtistName}]}},
                        "id": 1}))
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
                        log("Found: " + str(trackTitle) + " by: " + str(artist))
                        if (self.allowtrackrepeat == "true" or (trackPath not in self.addedTracks)):
                            if (self.preferdifferentartist != "true" or similarArtistName not in foundArtists):
                                listitem = self.getListItem(trackTitle,artist,album,thumb,fanart,duration,year,genre)
                                xbmc.PlayList(0).add(url=trackPath, listitem=listitem)
                                log("Add track : " + str(trackTitle) + " by: " + str(artist))
                                self.addedTracks += [trackPath]
                                xbmc.executebuiltin("Container.Refresh")
                                self.countFoundTracks += 1
                                if (similarArtistName not in foundArtists):
                                    foundArtists += [similarArtistName]
                            else:
                                log("Skipping - artist already added: " + similarArtistName)
                        else:
                            log("Skipping - repeat track: " + str(trackTitle))
                    else:
                        log("Skipping - artist already seen: " + str(artist))
            else:
                log("Not in library: " + similarTrackName + " - " + similarArtistName)

            if (self.countFoundTracks >= self.numberoftrackstoadd):
                break

        if (self.countFoundTracks == 0):
            time.sleep(3)
            log("None found")
            xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME+",No similar tracks were found)")
            return False

        xbmc.executebuiltin('SetCurrentPlaylist(0)')

    def getListItem(self, trackTitle, artist, album, thumb, fanart, duration, year, genre):
        listitem = xbmcgui.ListItem(trackTitle)
        if (fanart == ""):
            cache_name = xbmc.getCacheThumbName( str(artist) )
            fanart = "special://profile/thumbnails/Music/%s/%s" % ( "Fanart", cache_name, )
        listitem.setProperty('fanart_image',fanart)
        listitem.setInfo('music', { 'title': trackTitle, 'artist': artist, 'album': album, 'duration': duration, 'year': year, 'genre': genre, 'tracknumber': 0 })
        listitem.setArt({ 'thumb' : thumb, 'fanart' : fanart})
        return listitem

def addauto(newentry, scriptcode):
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
    autoexecfile = xbmcvfs.translatePath('special://home/userdata/autoexec.py')
    if exists(autoexecfile):
        with open(autoexecfile) as fh:
            lines = [ line for line in fh if not line.strip().endswith("#" + scriptcode) ]
        with open(autoexecfile, "w") as f:
            f.writelines(lines)

BASE_RESOURCE_PATH = os.path.join( __cwd__, "resources" )

process = os.path.join( BASE_RESOURCE_PATH , "pm.pid")

p=MyPlayer()
monitor = xbmc.Monitor()
while os.path.exists(process) and not monitor.abortRequested():
    if monitor.waitForAbort(1):
        if os.path.exists(process):
            os.remove(process)
            log("deleted pidfile")
        break
    xbmc.sleep(500)
log("process file gone, exiting")
