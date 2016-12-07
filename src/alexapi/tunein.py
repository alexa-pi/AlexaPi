from __future__ import unicode_literals

import ConfigParser as configparser

import logging
import re
import time
import urlparse

from collections import OrderedDict
from contextlib import closing

import requests

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO as StringIO
try:
    import xml.etree.cElementTree as elementtree
except ImportError:
    import xml.etree.ElementTree as elementtree

logging.basicConfig(filename='tunein.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)


class PlaylistError(Exception):
    pass


class Cache(object):
    # TODO: merge this to util library (copied from mopidy-spotify)

    def __init__(self, ctl=0, ttl=3600):
        self.cache = {}
        self.ctl = ctl
        self.ttl = ttl
        self._call_count = 0

    def __call__(self, func):
        def _memoized(*args):
            now = time.time()
            try:
                value, last_update = self.cache[args]
                age = now - last_update
                if self._call_count > self.ctl or age > self.ttl:
                    self._call_count = 0
                    raise AttributeError
                if self.ctl:
                    self._call_count += 1
                return value

            except (KeyError, AttributeError):
                value = func(*args)
                if value:
                    self.cache[args] = (value, now)
                return value

            except TypeError:
                return func(*args)

        def clear():
            self.cache.clear()

        _memoized.clear = clear
        return _memoized


def parse_m3u(data):
    # Copied from mopidy.audio.playlists
    # Mopidy version expects a header but it's not always present
    for line in data.readlines():
        if not line.startswith('#') and line.strip():
            yield line.strip()


def parse_pls(data):
    # Copied from mopidy.audio.playlists
    try:
        cp = configparser.RawConfigParser()
        cp.readfp(data)
    except configparser.Error:
        return

    for section in cp.sections():
        if section.lower() != 'playlist':
            continue
        for i in xrange(cp.getint(section, 'numberofentries')):
            try:
                # TODO: Remove this horrible hack to avoid adverts
                if cp.has_option(section, 'length%d' % (i + 1)):
                    if cp.get(section, 'length%d' % (i + 1)) == '-1':
                        yield cp.get(section, 'file%d' % (i + 1))
                else:
                    yield cp.get(section, 'file%d' % (i + 1))
            except configparser.NoOptionError:
                return


def fix_asf_uri(uri):
    return re.sub(r'http://(.+\?mswmext=\.asf)', r'mms://\1', uri, re.I)


def parse_old_asx(data):
    try:
        cp = configparser.RawConfigParser()
        cp.readfp(data)
    except configparser.Error:
        return
    for section in cp.sections():
        if section.lower() != 'reference':
            continue
        for option in cp.options(section):
            if option.lower().startswith('ref'):
                uri = cp.get(section, option).lower()
                yield fix_asf_uri(uri)


def parse_new_asx(data):
    # Copied from mopidy.audio.playlists
    try:
        for _, element in elementtree.iterparse(data):
            element.tag = element.tag.lower()  # normalize
            for ref in element.findall('entry/ref[@href]'):
                yield fix_asf_uri(ref.get('href', '').strip())

            for entry in element.findall('entry[@href]'):
                yield fix_asf_uri(entry.get('href', '').strip())
    except elementtree.ParseError:
        return


def parse_asx(data):
    if 'asx' in data.getvalue()[0:50].lower():
        return parse_new_asx(data)
    else:
        return parse_old_asx(data)


# This is all broken: mopidy/mopidy#225
# from gi.repository import TotemPlParser
# def totem_plparser(uri):
#     results = []
#     def entry_parsed(parser, uri, metadata):
#         results.append(uri)

#     parser = TotemPlParser.Parser.new()
#     someid = parser.connect('entry-parsed', entry_parsed)
#     res = parser.parse(uri, False)
#     parser.disconnect(someid)
#     if res != TotemPlParser.ParserResult.SUCCESS:
#         logger.debug('Failed to parse playlist')
#     return results


def find_playlist_parser(extension, content_type):
    extension_map = {'.asx': parse_asx,
                     '.wax': parse_asx,
                     '.m3u': parse_m3u,
                     '.pls': parse_pls}
    content_type_map = {'video/x-ms-asf': parse_asx,
                        'application/x-mpegurl': parse_m3u,
                        'audio/x-scpls': parse_pls}

    parser = extension_map.get(extension, None)
    if not parser and content_type:
        # Annoying case where the url gave us no hints so try and work it out
        # from the header's content-type instead.
        # This might turn out to be server-specific...
        parser = content_type_map.get(content_type.lower(), None)
    return parser


class TuneIn(object):
    """Wrapper for the TuneIn API."""

    def __init__(self, timeout, session=None):
        self._base_uri = 'http://opml.radiotime.com/%s'
        self._session = session or requests.Session()
        self._timeout = timeout / 1000.0
        self._stations = {}

    def reload(self):
        self._stations.clear()
        self._tunein.clear()	# pylint: disable=no-member
        self._get_playlist.clear()      # pylint: disable=no-member

    def _flatten(self, data):
        results = []
        for item in data:
            if 'children' in item:
                results.extend(item['children'])
            else:
                results.append(item)
        return results

    def _filter_results(self, data, section_name=None, map_func=None):
        results = []

        def grab_item(item):
            if 'guide_id' not in item:
                return
            if map_func:
                station = map_func(item)
            elif item.get('type', 'link') == 'link':
                results.append(item)
                return
            else:
                station = item
            self._stations[station['guide_id']] = station
            results.append(station)

        for item in data:
            if section_name is not None:
                section_key = item.get('key', '').lower()
                if section_key.startswith(section_name.lower()):
                    for child in item['children']:
                        grab_item(child)
            else:
                grab_item(item)
        return results

    def categories(self, category=''):
        if category == 'location':
            args = '&id=r0'  # Annoying special case
        elif category == 'language':
            args = '&c=lang'
            return []  # TuneIn's API is a mess here, cba
        else:
            args = '&c=' + category

        # Take a copy so we don't modify the cached data
        results = list(self._tunein('Browse.ashx', args))
        if category in ('podcast', 'local'):
            # Flatten the results!
            results = self._filter_results(self._flatten(results))
        elif category == '':
            trending = {'text': 'Trending',
                        'key': 'trending',
                        'type': 'link',
                        'URL': self._base_uri % 'Browse.ashx?c=trending'}
            # Filter out the language root category for now
            results = [x for x in results if x['key'] != 'language']
            results.append(trending)
        else:
            results = self._filter_results(results)
        return results

    def locations(self, location):
        args = '&id=' + location
        results = self._tunein('Browse.ashx', args)
        # TODO: Support filters here
        return [x for x in results if x.get('type', '') == 'link']

    def _browse(self, section_name, guide_id):
        args = '&id=' + guide_id
        results = self._tunein('Browse.ashx', args)
        return self._filter_results(results, section_name)

    def featured(self, guide_id):
        return self._browse('Featured', guide_id)

    def local(self, guide_id):
        return self._browse('Local', guide_id)

    def stations(self, guide_id):
        return self._browse('Station', guide_id)

    def related(self, guide_id):
        return self._browse('Related', guide_id)

    def shows(self, guide_id):
        return self._browse('Show', guide_id)

    def episodes(self, guide_id):
        args = '&c=pbrowse&id=' + guide_id
        results = self._tunein('Tune.ashx', args)
        return self._filter_results(results, 'Topic')

    def _map_listing(self, listing):
        # We've already checked 'guide_id' exists
        url_args = 'Tune.ashx?id=%s' % listing['guide_id']
        return {'text': listing.get('name', '???'),
                'guide_id': listing['guide_id'],
                'type': 'audio',
                'image': listing.get('logo', ''),
                'subtext': listing.get('slogan', ''),
                'URL': self._base_uri % url_args}

    def _station_info(self, station_id):
        logger.debug('Fetching info for station %s', station_id)
        args = '&c=composite&detail=listing&id=' + station_id
        results = self._tunein('Describe.ashx', args)
        listings = self._filter_results(results, 'Listing', self._map_listing)
        if listings:
            return listings[0]

    def parse_stream_url(self, url):
        logger.debug('Extracting URIs from %s', url)
        extension = urlparse.urlparse(url).path[-4:]
        if extension in ['.mp3', '.wma']:
            logger.debug('Got %s', url)
            return [url]  # Catch these easy ones
        results = []
        playlist, content_type = self._get_playlist(url)
        if playlist:
            parser = find_playlist_parser(extension, content_type)
            if parser:
                playlist_data = StringIO.StringIO(playlist)
                try:
                    results = [u for u in parser(playlist_data)
                               if u and u != url]
                except Exception as exp:   # pylint: disable=broad-except
                    logger.error('TuneIn playlist parsing failed %s', exp)
                if not results:
                    logger.debug('Parsing failure, '
                                 'malformed playlist: %s', playlist)
        elif content_type:
            results = [url]
        logger.debug('Got %s', results)
        return list(OrderedDict.fromkeys(results))

    def tune(self, station):
        logger.debug('Tuning station id %s', station['guide_id'])
        args = '&id=' + station['guide_id']
        stream_uris = []
        for stream in self._tunein('Tune.ashx', args):
            if 'url' in stream:
                stream_uris.append(stream['url'])
        if not stream_uris:
            logger.error('Failed to tune station id %s', station['guide_id'])
        return list(OrderedDict.fromkeys(stream_uris))

    def station(self, station_id):
        if station_id in self._stations:
            station = self._stations[station_id]
        else:
            station = self._station_info(station_id)
            self._stations['station_id'] = station
        return station

    def search(self, query):
        # "Search.ashx?query=" + query + filterVal
        if not query:
            logger.debug('Empty search query')
            return []
        logger.debug('Searching TuneIn for "%s"', query)
        args = '&query=' + query
        search_results = self._tunein('Search.ashx', args)
        results = []
        for item in self._flatten(search_results):
            if item.get('type', '') == 'audio':
                # Only return stations
                self._stations[item['guide_id']] = item
                results.append(item)

        return results

    @Cache()
    def _tunein(self, variant, args):
        uri = (self._base_uri % variant) + '?render=json' + args
        logger.debug('TuneIn request: %s', uri)
        try:
            with closing(self._session.get(uri, timeout=self._timeout)) as resp:
                resp.raise_for_status()
                return resp.json()['body']
        except Exception as exp:   # pylint: disable=broad-except
            logger.info('TuneIn API request for %s failed: %s', variant, exp)
        return {}

    @Cache()
    def _get_playlist(self, uri):
        data, content_type = None, None
        try:
            # Defer downloading the body until know it's not a stream
            with closing(self._session.get(uri,
                                           timeout=self._timeout,
                                           stream=True)) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get('content-type', 'audio/mpeg')
                logger.debug('%s has content-type: %s', uri, content_type)
                if content_type != 'audio/mpeg':
                    data = resp.content.decode('utf-8', errors='ignore')
        except Exception as exp:   # pylint: disable=broad-except
            logger.info('TuneIn playlist request for %s failed: %s', uri, exp)
        return (data, content_type)
