"""
    Script for generating smart playlists based on a seeding track and last.fm api
    Created by: ErlendSB
    Ported to python3 by d0nk0tr0n
"""
import os
import random
import difflib
import time
import threading
import unicodedata
import urllib.request
import urllib.parse
import re
from os.path import exists
import json as simplejson
import xbmc, xbmcgui, xbmcaddon, xbmcvfs

__settings__ = xbmcaddon.Addon(id='script.lastfmplaylistgenerator')
__cwd__       = __settings__.getAddonInfo('path')

# -------------------------------------------------------------------------
# Module-level helpers
# -------------------------------------------------------------------------

def log(*args):
    message = 'LPM: ' + ' '.join(str(a.decode('utf-8') if isinstance(a, bytes) else a) for a in args)
    xbmc.log(msg=message, level=xbmc.LOGWARNING)
    #xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def sanitize(text):
    return (text.replace("+", " ")
                .replace("(", " ")
                .replace(")", " ")
                .replace("&quot", "''")
                .replace("&amp;", "and"))

def fetch_url(url):
    log("Request :", url)
    with urllib.request.urlopen(url) as sock:
        return sock.read().decode('utf-8')

def has_songs(response):
    return (
        'result' in response
        and response['result'] is not None
        and 'songs' in response['result']
    )

def build_song_query(title, artist, operator):
    return (
        '{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", '
        '"params": { "properties": ["title", "artist", "album", "file", "thumbnail", "duration", "fanart", "year", "genre"], '
        '"limits": {"end":1}, "sort": {"method":"random"}, '
        '"filter": { "and":[{"field":"title","operator":"%s","value":"%s"},'
        '{"field":"artist","operator":"%s","value":"%s"}] } }, "id": 1}'
    ) % (operator, title, operator, artist)

def find_song_in_library(title, artist):
    response = simplejson.loads(xbmc.executeJSONRPC(build_song_query(title, artist, "is")))
    if not has_songs(response):
        response = simplejson.loads(xbmc.executeJSONRPC(build_song_query(title, artist, "contains")))
    return response

def addauto(newentry, scriptcode):
    log("addauto started")
    autoexecfile = xbmcvfs.translatePath('special://home/userdata/autoexec.py')
    if exists(autoexecfile):
        with open(autoexecfile) as fh:
            lines = list(fh.readlines())
        has_import_xbmc = any("import xbmc" in line for line in lines)
        has_import_os   = any("import os" in line for line in lines)
        lines.append("import time"   + "#" + scriptcode + "\n")
        lines.append("time.sleep(2)" + "#" + scriptcode + "\n")
        lines.append(newentry        + "#" + scriptcode + "\n")
        with open(autoexecfile, "w") as f:
            if not has_import_xbmc:
                f.write("import xbmc" + "#" + scriptcode + "\n")
            if not has_import_os:
                f.write("import os"   + "#" + scriptcode + "\n")
            f.writelines(lines)
    else:
        with open(autoexecfile, "w") as f:
            f.write("import time"   + "#" + scriptcode + "\n")
            f.write("time.sleep(2)" + "#" + scriptcode + "\n")
            f.write("import os"     + "#" + scriptcode + "\n")
            f.write("import xbmc"   + "#" + scriptcode + "\n")
            f.write(newentry        + "#" + scriptcode + "\n")

def removeauto(scriptcode):
    log("removeauto started")
    autoexecfile = xbmcvfs.translatePath('special://home/userdata/autoexec.py')
    if exists(autoexecfile):
        with open(autoexecfile) as fh:
            lines = [line for line in fh if not line.strip().endswith("#" + scriptcode)]
        with open(autoexecfile, "w") as f:
            f.writelines(lines)


# -------------------------------------------------------------------------
# Player class
# -------------------------------------------------------------------------

class MyPlayer(xbmc.Player):
    SCRIPT_NAME = "LAST.FM Playlist Generator"
    API_PATH    = "http://ws.audioscrobbler.com/2.0/?api_key=3ae834eee073c460a250ee08979184ec"

    def __init__(self):
        self.addedTracks           = []
        self.countFoundTracks      = 0
        self.currentSeedingTrack   = 0
        self.firstRun              = 0
        self.dbtype                = 'sqlite3'
        self.timeStarted           = time.time()
        self.timer                 = None

        self.allowtrackrepeat      = __settings__.getSetting("allowtrackrepeat")
        self.preferdifferentartist = __settings__.getSetting("preferdifferentartist")
        self.numberoftrackstoadd   = (1, 2, 3, 5, 10)[int(__settings__.getSetting("numberoftrackstoadd"))]
        self.delaybeforesearching  = (2, 5, 10, 30)[int(__settings__.getSetting("delaybeforesearching"))]
        self.limitlastfmresult     = (50, 100, 250)[int(__settings__.getSetting("limitlastfmresult"))]
        self.minimalplaycount      = (50, 100, 250, 500)[int(__settings__.getSetting("minimalplaycount"))]
        self.minimalmatching       = (1, 2, 5, 10, 20)[int(__settings__.getSetting("minimalmatching"))]
        self.mode                  = ("Similar tracks", "Top tracks of similar artist", "Custom")[int(__settings__.getSetting("mode"))]

        log("__init__ started")
        self._detect_db_type()
        xbmc.Player.__init__(self)
        xbmc.PlayList(0).clear()
        self.firstRun = 1

        process = self._get_pid_path()
        removeauto('lastfmplaylistgeneratorpm')
        addauto(
            "if os.path.exists('" + os.path.normpath(process).replace('\\', '\\\\') + "'):#lastfmplaylistgeneratorpm\n\tos.remove('" + os.path.normpath(process).replace('\\', '\\\\') + "')",
            'lastfmplaylistgeneratorpm'
        )
        xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME + ",Start by playing a song)")
        log("__init__ completed")

    def _get_pid_path(self):
        return os.path.join(__cwd__, "resources", "pm.pid")

    def _detect_db_type(self):
        settings_path = xbmcvfs.translatePath("special://userdata/advancedsettings.xml")
        if not os.path.exists(settings_path):
            self.dbtype = 'sqlite3'
            return
        from xml.etree.ElementTree import ElementTree
        tree = ElementTree()
        tree.parse(settings_path)
        music_db = tree.getroot().find("musicdatabase")
        if music_db is not None:
            for setting in music_db:
                if setting.tag == 'type':
                    self.dbtype = setting.text
        else:
            self.dbtype = 'sqlite3'

    def _should_add_track(self, trackPath, artist, foundArtists):
        if self.allowtrackrepeat not in ("true", 1):
            if trackPath in self.addedTracks:
                return False
        if self.preferdifferentartist in ("true", 1):
            if artist in foundArtists:
                return False
        return True

    def _playlist_has_room(self):
        playlist  = xbmc.PlayList(0)
        remaining = playlist.size() - playlist.getposition()
        return remaining < self.numberoftrackstoadd + 1

    def unicode_normalize_string(self, text):
        return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').upper().replace(b"-", b"")

    def onPlayBackStarted(self):
        log("onPlayBackStarted waiting:", str(self.delaybeforesearching), "seconds")
        if self.timer is not None and self.timer.is_alive():
            self.timer.cancel()
        self.timer = threading.Timer(self.delaybeforesearching, self.startPlayBack)
        self.timer.start()

    def startPlayBack(self):
        log("startPlayBack started")
        player = xbmc.Player()
        if not player.isPlayingAudio():
            return

        tag    = player.getMusicInfoTag()
        title  = tag.getTitle()
        artist = tag.getArtist()
        log("Artist: ", artist, "-", title, "started playing")
        self.countFoundTracks = 0

        if self.firstRun == 1:
            self.firstRun = 0
            log("Playing file:", tag.getURL())
            listitem = self.getListItem(
                title, artist,
                tag.getAlbum(),
                xbmc.getInfoLabel("Player.Art(thumb)"),
                xbmc.getInfoLabel("Player.Art(fanart)"),
                tag.getDuration(),
                tag.getYear(),
                tag.getGenre()
            )
            xbmc.PlayList(0).clear()
            xbmc.executebuiltin('XBMC.ActivateWindow(10500)')
            xbmc.PlayList(0).add(url=tag.getURL(), listitem=listitem)
            self.addedTracks.append(tag.getURL())

        log("main_similarTracks stopping next")
        self.main_similarTracks(title, artist)

    def fetch_similarTracks(self, title, artist):
        url    = self.API_PATH + "&method=track.getsimilar&limit=" + str(self.limitlastfmresult) + "&artist=" + urllib.parse.quote_plus(artist) + "&track=" + urllib.parse.quote_plus(title)
        html   = fetch_url(url)
        tracks = re.findall(
            r"<track>.*?<name>(.+?)</name>.*?<playcount>(.+?)</playcount>.*?<match>(.+?)</match>.*?<artist>.*?<name>(.+?)</name>.*?</artist>.*?</track>",
            html, re.DOTALL
        )
        tracks = [x for x in tracks if int(x[1]) > self.minimalplaycount]
        tracks = [x for x in tracks if float(x[2]) > (float(self.minimalmatching) / 100.0)]
        return tracks

    def fetch_similarArtists(self, artist):
        url     = self.API_PATH + "&method=artist.getsimilar&limit=50&artist=" + urllib.parse.quote_plus(artist)
        html    = fetch_url(url)
        artists = re.findall(
            r"<artist>.*?<name>(.+?)</name>.*?<mbid>(.+?)</mbid>.*?<match>(.+?)</match>.*?</artist>",
            html, re.DOTALL
        )
        return [x for x in artists if float(x[2]) > (float(self.minimalmatching) / 100.0)]

    def fetch_topTracksOfArtist(self, mbid):
        url    = self.API_PATH + "&method=artist.gettoptracks&limit=20&mbid=" + urllib.parse.quote_plus(mbid)
        html   = fetch_url(url)
        tracks = re.findall(
            r"<track rank=.+?>.*?<name>(.+?)</name>.*?<playcount>(.+?)</playcount>.*?<listeners>(.+?)</listeners>.*?<artist>.*?<name>(.+?)</name>.*?</artist>.*?</track>",
            html, re.DOTALL
        )
        log("Count:", str(len(tracks)))
        return [x for x in tracks if int(x[1]) > self.minimalplaycount]

    def find_Artist(self, artistName):
        query    = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": { "filter": {"field":"artist","operator":"is","value":"%s"} }, "id": 1}' % artistName
        response = simplejson.loads(xbmc.executeJSONRPC(query))
        return 'result' in response and response['result'] is not None and 'artists' in response['result']

    def main_similarTracks(self, title, artist):
        if not self._playlist_has_room():
            log("Playlist already has enough tracks, skipping search")
            return

        similar = []
        count   = 0
        if self.mode in ("Similar tracks", "Custom"):
            similar += self.fetch_similarTracks(title, artist)
            count = len(similar)
        if self.mode == "Top tracks of similar artist" or (self.mode == "Custom" and count < 10):
            similar_artists = self.fetch_similarArtists(artist)
            log("No Similar Artists:", str(len(similar_artists)))
            for artistName, mbid, _ in similar_artists:
                if self.find_Artist(artistName):
                    similar += self.fetch_topTracksOfArtist(mbid)

        log("Count:", str(len(similar)))
        random.shuffle(similar)

        selectedArtist = []
        foundArtists   = []

        for track in similar:
            trackName  = sanitize(track[0])
            artistName = sanitize(track[3])
            log("Looking for:", trackName, "-", artistName)

            response = find_song_in_library(trackName, artistName)
            if not has_songs(response):
                continue

            for item in response['result']['songs']:
                found_artist = item["artist"][0] if item["artist"] else ""
                if found_artist in selectedArtist:
                    continue
                selectedArtist.append(found_artist)

                trackTitle = item["title"]
                trackPath  = item["file"]
                log("Found:", trackTitle, "by:", found_artist)

                if not self._should_add_track(trackPath, found_artist, foundArtists):
                    continue

                listitem = self.getListItem(
                    trackTitle, found_artist, item["album"],
                    item["thumbnail"], item["fanart"],
                    int(item["duration"]), int(item["year"]), item["genre"]
                )
                xbmc.PlayList(0).add(url=trackPath, listitem=listitem)
                log("Add track:", trackTitle, "by:", found_artist)
                self.addedTracks.append(trackPath)
                xbmc.executebuiltin("Container.Refresh")
                self.countFoundTracks += 1
                if found_artist not in foundArtists:
                    foundArtists.append(found_artist)

            if self.countFoundTracks >= self.numberoftrackstoadd:
                break

        if self.countFoundTracks == 0:
            log("None found")
            xbmc.executebuiltin("Notification(" + self.SCRIPT_NAME + ",No similar tracks were found)")
            return False

        xbmc.executebuiltin('SetCurrentPlaylist(0)')

    def getListItem(self, trackTitle, artist, album, thumb, fanart, duration, year, genre):
        log("getListItem started")
        listitem = xbmcgui.ListItem(trackTitle)
        if not fanart:
            cache_name = xbmc.getCacheThumbName(str(artist))
            fanart = "special://profile/thumbnails/Music/Fanart/%s" % cache_name
        listitem.setArt({'thumb': thumb, 'fanart': fanart})
        log("Fanart:", fanart)
        log("Thumb:", thumb)
        tag = listitem.getMusicInfoTag()
        tag.setTitle(trackTitle)
        tag.setArtist(artist)
        tag.setAlbum(album)
        tag.setDuration(duration)
        tag.setYear(year)
        tag.setGenres(genre if isinstance(genre, list) else [str(genre)])
        return listitem


# -------------------------------------------------------------------------
# Entry point
# -------------------------------------------------------------------------

process = os.path.join(__cwd__, "resources", "pm.pid")
p       = MyPlayer()
monitor = xbmc.Monitor()

log("pm.py main loop started")
while True:
    if not os.path.exists(process):
        log("pm.py pidfile gone, exiting")
        break
    if monitor.waitForAbort(1):
        os.remove(process)
        log("deleted pidfile, kodi abort requested")
        break
    xbmc.sleep(500)

log("pm.py exiting")
