#!/bin/bash
# Check which artists in the Kodi music library require unicode normalization
# to match Last.fm results.
#
# Usage:
#   SQLite (default):  ./check_normalization.sh
#   SQLite (custom):   ./check_normalization.sh /path/to/MyMusic83.db
#   MySQL:             ./check_normalization.sh mysql

MYSQL_USER="kodi"
MYSQL_PASS="kodi"
MYSQL_HOST="dock01"
MYSQL_DB="MyMusic83"

if [ "$1" = "mysql" ]; then
    mysql -u "$MYSQL_USER" -p"$MYSQL_PASS" -h "$MYSQL_HOST" -N -e \
      "SELECT strArtist FROM artist ORDER BY strArtist" "$MYSQL_DB"
else
    DB_PATH="${1:-/home/donk/.var/app/tv.kodi.Kodi/data/userdata/Database/MyMusic83.db}"
    sqlite3 "$DB_PATH" "SELECT strArtist FROM artist ORDER BY strArtist"
fi | python3 -c "
import sys, html, unicodedata

def normalize(text):
    text = html.unescape(text)
    text = text.replace('\u2018', \"'\").replace('\u2019', \"'\").replace('\u201c', '\"').replace('\u201d', '\"')
    text = text.replace('\u2010', '-').replace('\u2011', '-').replace('\u2012', '-').replace('\u2013', '-').replace('\u2014', '-')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text

for line in sys.stdin:
    artist = line.rstrip()
    normalized = normalize(artist)
    if normalized != artist:
        print(repr(artist) + ' -> ' + repr(normalized))
"
