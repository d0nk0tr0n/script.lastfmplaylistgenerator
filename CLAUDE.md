# CLAUDE.md — script.lastfmplaylistgenerator

## Project Overview

**Last.FM Playlist Generator (Partymode)** is a Kodi addon (version 1.3.1.2) that generates iTunes Genius-style dynamic playlists. When a user plays a song, the addon queries the Last.FM API to find similar tracks and automatically appends them to the Kodi playlist. It is written in Python 3 and targets the Kodi/XBMC Python API (xbmc.python 3.0.0+).

**Addon ID:** `script.lastfmplaylistgeneratorPM`  
**Provider:** d0nk0tr0n  
**Original author:** ErlendSB (Python 2), ported to Python 3 by d0nk0tr0n

---

## Repository Structure

```
script.lastfmplaylistgenerator/
├── addon.xml                      # Addon manifest (ID, version, dependencies)
├── default.py                     # Entry point: manages pid file, launches pm.py
├── pm.py                          # Core logic: MyPlayer class, Last.FM API calls
├── changelog.txt                  # Version history
├── icon.png                       # Addon icon
├── LICENSE.txt                    # License
├── README.md                      # User-facing documentation
└── resources/
    ├── settings.xml               # Addon settings schema (Kodi settings UI)
    └── language/
        ├── English/strings.xml    # Legacy English strings
        ├── French/strings.xml     # French translations
        ├── Polish/strings.xml     # Polish translations
        └── resource.language.en_gb/
            ├── langinfo.xml
            ├── strings.po         # Modern Kodi PO-format strings (canonical)
            └── strings.xml        # Modern Kodi XML strings
```

---

## Key Files

### `default.py` — Entry Point
- Checks for a PID file at `resources/pm.pid`
- If the PID file **exists**: prompts user to stop the generator and removes the file
- If the PID file **does not exist**: writes the current process PID to it, then `import pm` to start the generator
- Logging via `xbmc.log` at `LOGERROR` level

### `pm.py` — Core Logic

Contains the `MyPlayer` class (extends `xbmc.Player`) and two module-level helper functions.

#### `MyPlayer` class
All settings are read from the Kodi addon settings at class definition time (class-level attributes):

| Attribute | Setting ID | Options |
|---|---|---|
| `allowtrackrepeat` | `allowtrackrepeat` | bool |
| `preferdifferentartist` | `preferdifferentartist` | bool |
| `numberoftrackstoadd` | `numberoftrackstoadd` | 1, 2, 3, 5, 10 |
| `delaybeforesearching` | `delaybeforesearching` | 2, 5, 10, 30 (seconds) |
| `limitlastfmresult` | `limitlastfmresult` | 50, 100, 250 |
| `minimalplaycount` | `minimalplaycount` | 50, 100, 250, 500 |
| `minimalmatching` | `minimalmatching` | 1, 2, 5, 10, 20 (percent) |
| `mode` | `mode` | "Similar tracks", "Top tracks of similar artist", "Custom" |

**Key methods:**
- `__init__`: Detects DB type (sqlite3 vs mysql via `advancedsettings.xml`), clears playlist, registers cleanup in `autoexec.py`
- `onPlayBackStarted`: Schedules `startPlayBack` after `delaybeforesearching` seconds using `threading.Timer`; cancels any pending timer first
- `startPlayBack`: On first run, seeds the playlist with the currently playing track; always calls `main_similarTracks`
- `main_similarTracks`: Orchestrates the fetch strategy based on `mode`, shuffles results, queries Kodi's AudioLibrary via JSON-RPC, adds matching tracks to `xbmc.PlayList(0)`
- `fetch_similarTracks`: Calls `track.getsimilar` Last.FM API, filters by playcount and similarity
- `fetch_similarArtists`: Calls `artist.getsimilar` Last.FM API, filters by match percentage
- `fetch_topTracksOfArtist`: Calls `artist.gettoptracks` Last.FM API by MBID, filters by playcount
- `fetch_searchTrack`: Calls `track.search` Last.FM API (currently unused/commented out in `main_similarTracks`)
- `getListItem`: Creates an `xbmcgui.ListItem` with full music metadata (title, artist, album, duration, year, genre, thumb, fanart)

**Module-level helpers:**
- `addauto(newentry, scriptcode)`: Appends cleanup code to Kodi's `special://home/userdata/autoexec.py`
- `removeauto(scriptcode)`: Removes lines tagged with `scriptcode` from `autoexec.py`

**Main loop** (module-level, runs after `MyPlayer()` is instantiated):
```python
p = MyPlayer()
while(1):
    if os.path.exists(process):
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                os.remove(process)
        else:
            break
```

---

## Addon Settings (`resources/settings.xml`)

String IDs are defined in `resources/language/` files. The canonical modern format is `resource.language.en_gb/strings.po` (IDs 33000–33007).

| ID | Label | Type | Default |
|---|---|---|---|
| 33000 | Allow same track more than once | bool | false |
| 33001 | Prefer different artist | bool | false |
| 33002 | Preferred number of tracks to add | enum | 2 (value: 3) |
| 33003 | Seconds delay before searching | enum | 0 (value: 2s) |
| 33004 | Limit lastfm results | enum | 2 (value: 250) |
| 33005 | Minimum listening count on last.fm | enum | 1 (value: 100) |
| 33006 | Minimum percentage similarity | enum | 1 (value: 2%) |
| 33007 | Search mode | enum | 2 (value: Custom) |

---

## Last.FM API

**API base:** `http://ws.audioscrobbler.com/2.0/?api_key=3ae834eee073c460a250ee08979184ec`

Methods used:
- `track.getsimilar` — find similar tracks to seed
- `artist.getsimilar` — find similar artists
- `artist.gettoptracks` — top tracks of a similar artist (by MBID)
- `track.search` — (legacy, currently commented out)

Responses are parsed with **regex** (`re.findall`) directly on the XML response body — not with an XML parser.

---

## Known Issues / TODOs in Code

1. **`xbmc.translatePath` deprecation** (`pm.py:20`): The code has already been updated to use `xbmcvfs.translatePath`, but the TODO comment remains.
2. **`unicode_normalize_string` bug** (`pm.py:122`): `unicodedata.normalize(text)` is called with only one argument — it requires two (`form` + `unistr`). This method is currently commented out everywhere it was used, so it is not called at runtime.
3. **`fetch_searchTrack` bug** (`pm.py:149`): `log("main foundTracks is " + foundTracks)` — `foundTracks` is a list, not a string; this would raise a `TypeError`. This method is unreachable (commented out in `main_similarTracks`).
4. **Listener count comparison** (`pm.py:140`): `foundListeners > self.minimalplaycount` compares a string from regex to an int — this is a latent bug in the unused `fetch_searchTrack` path.
5. **`addedTracks` encoding inconsistency** (`pm.py:105` vs `pm.py:274`): Initial seed appends a plain string; subsequent tracks append `trackPath.encode('utf-8')` (bytes). Deduplication check will always fail for the seed track.

---

## Development Conventions

### Language & Runtime
- Python 3 only (ported from Python 2 in v1.3.0.2)
- Kodi/XBMC addon environment — the `xbmc`, `xbmcgui`, `xbmcaddon`, `xbmcvfs` modules are only available at runtime inside Kodi
- No external Python package dependencies; uses only stdlib + Kodi APIs + `script.module.simplejson` (though `json` from stdlib is actually imported as `simplejson` in `pm.py`)

### Logging
- `default.py`: logs at `xbmc.LOGERROR`
- `pm.py`: logs at `xbmc.LOGWARNING` during development; switch to `xbmc.LOGDEBUG` for release (see comment at `pm.py:29–31`)
- All log messages are prefixed with `"LPM: "`

### String IDs
- All user-visible strings use numeric IDs (33000+) defined in `resources/language/`
- The PO file at `resource.language.en_gb/strings.po` is the canonical modern format
- Legacy `strings.xml` files (English, French, Polish) are kept for backward compatibility

### Versioning
- Version string is in `addon.xml` (attribute `version`)
- Changelog maintained in `changelog.txt` in reverse-chronological order

### PID File
- `resources/pm.pid` is used as a runtime lock/signal file
- It is created by `default.py` and removed on exit via `autoexec.py` cleanup hooks
- Never commit a `pm.pid` file (it is a runtime artifact)

---

## Installation / Testing

This addon **cannot be run standalone** — it requires a running Kodi instance. To test:

1. Copy/symlink the addon directory into Kodi's addon directory (e.g., `~/.kodi/addons/script.lastfmplaylistgeneratorPM/`)
2. Enable the addon in Kodi's addon manager
3. Configure settings via the addon's settings screen
4. Play a music track, then run the addon from Programs

There are no unit tests in this repository. All testing is manual within a Kodi environment.

---

## Branch Strategy

- `master`: stable releases
- Feature/fix branches are merged via PR (see PRs #1–#3 in history)
- Current development branch for AI-assisted work: `claude/add-claude-documentation-ojPKH`
