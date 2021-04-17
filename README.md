# script.lastfmplaylistgenerator
Kodi Plugin - LastFMPlaylistGenerator (emulates Apple iTunes Genius)

This kodi addon generates a genuis-like playlist based on the currently playing track. The addon needs partymode disabled, so the first time launching, it will prompt to disable partymode, then run the addon again. The second time, it will prompt to select a song. This will be the seed that populates the playlist. As it plays, additional songs will be added based on the various scrobbles to Last.FM.


Some of the settings explained:
"Preferred number of tracks to add":
  Number of tracks to add from Last.FM

"Seconds delay before searching"
  How long to wait before scraping Last.FM for tracks

"Limit lastfm results"
  Number of results grabbed from Last.FM to match against (lower number for better similarity)

"Minimum number of listening on last.fm"
  The more people listening, the more popular the song (higher number for better songs)

"Minimum Percentage similarity"
  Similarity of tracks that should match in Last.FM (higher number for better similarity)
