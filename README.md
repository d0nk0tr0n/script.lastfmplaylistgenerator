# script.lastfmplaylistgenerator

Kodi addon that generates smart playlists based on the currently playing track using the Last.fm API. Similar to Apple iTunes Genius or Spotify radio.

## How it works

1. Start the addon from the Kodi addon menu
2. Play any song — this becomes the seed track
3. The addon queries Last.fm for similar tracks and matches them against your Kodi music library
4. Matching tracks are added to the playlist automatically as each song plays

The addon supports three modes:
- **Similar tracks** — finds tracks similar to the currently playing song
- **Top tracks of similar artist** — finds top tracks from artists similar to the current artist
- **Custom** — tries similar tracks first, falls back to similar artist top tracks if fewer than 10 results

## Features

- Last.fm autocorrect enabled — handles artist name variants (e.g. Beyonce → Beyoncé, Blue Oyster Cult → Blue Öyster Cult)
- MusicBrainz ID used for Last.fm queries when available, bypassing name matching issues entirely
- Unicode normalization for library matching (diacritics, smart quotes, fancy dashes)
- HTML entity unescaping for Last.fm results
- Strips live/remaster/featuring suffixes for better Last.fm matching
- Artist existence cached per search run — skips all track queries for artists not in the library
- Multi-tier library search fallback (exact, contains, normalized, smart-quote variants)
- Top tracks of similar artists sorted by listener count
- Configurable track repeat and artist diversity preferences
- Single-instance enforcement via pid file
- Caps similar artist API calls to avoid excessive Last.fm requests

## Settings

| Setting | Description | Values |
|---------|-------------|--------|
| Allow track repeat | Allow the same track to appear multiple times | on/off |
| Prefer different artist | Avoid consecutive tracks from the same artist | on/off |
| Number of tracks to add | How many tracks to add per seed | 1, 2, 3, 5, 10 |
| Seconds delay before searching | Wait time before querying Last.fm after a song starts | 2, 5, 10, 30 |
| Limit Last.fm results | Max results from Last.fm per query (lower = better similarity) | 50, 100, 250 |
| Minimum listening count | Minimum Last.fm scrobbles required (higher = more popular) | 1K, 10K, 50K, 100K, 250K, 500K, 1M |
| Minimum percentage similarity | Similarity threshold for track matching | 1%, 2%, 5%, 10%, 20% |
| Search mode | Strategy for finding similar tracks | Similar tracks, Top tracks of similar artist, Custom |

## Requirements

- Kodi with a music library
- No external account needed — uses the free Last.fm API

## Tools

- `resources/check_normalization.sh` — audit which artists in your Kodi library have unicode characters that require normalization. Supports both SQLite and MySQL Kodi databases.
