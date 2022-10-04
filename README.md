Stores knowledge and data necessary to properly use links from OpenStreetMap to Wikipedia, Wikidata and Wikimedia Commons.

# Installation

It has a very unfortunate dependecies - sorry for that, pull requests improving this situation are welcome.

- first you need to clone, modify and install as a python package [this thing](https://codeberg.org/matkoniecz/osm_handling_config) - pull request providing cache location in a better way (config file? environment variable?) is welcome

# Running tests

`python3 -m unittest`

# Fixing Wikidata

Search for `too_abstract_or_wikidata_bugs` and disable that to get more errors caused by Wikidata
