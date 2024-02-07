import glob
import os

from wikimedia_connection import wikimedia_connection


def helper_setup_module():

    cachepath = 'tests_cache'
    if not os.path.exists(cachepath):
        os.makedirs(cachepath)

    # TODO Find a better solution for this
    # files = glob.glob(cachepath + '/wikimedia-connection-cache/wikidata_by_id/*')
    # for f in files:
    #    os.remove(f)

    wikimedia_connection.set_cache_location(cachepath)

