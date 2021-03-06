#VERSION: 0.21
#AUTHORS: Bugsbringer (dastins193@gmail.com)


EMAIL = "YOUR_EMAIL"
PASSWORD = "YOUR_PASSWORD"
ENABLE_PEERS_INFO = True
SITE_URL = "https://www.lostfilm.tv"

proxy = {
    'enable': False,

    'proxy_urls': {
        'http': 'ip:port',
        'https': 'ip:port'
    },

    'auth': False,
    'username': '',
    'password': ''
}

import concurrent.futures
import hashlib
import json
import logging
import os
import re
from collections import OrderedDict
from datetime import datetime
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from io import BytesIO
from random import randint
from urllib import parse, request

from novaprinter import prettyPrinter


STORAGE = os.path.abspath(os.path.dirname(__file__))
is_main = __name__ == '__main__'

# logging
log_config = {
    'level': 'DEBUG' if is_main else 'ERROR',
    'format': '[%(asctime)s] %(levelname)s:%(name)s:%(funcName)s - %(message)s',
    'datefmt': '%d-%b-%y %H:%M:%S'
}

if not is_main:
    log_config.update({'filename': os.path.join(STORAGE, 'lostfilm.log')})

logging.basicConfig(**log_config)
logger = logging.getLogger('lostfilm')
logger.setLevel(logging.WARNING)


class lostfilm:
    url = SITE_URL
    name = 'LostFilm'
    supported_categories = {'all': '0'}

    search_url_pattern = SITE_URL + '/search/?q={what}'
    serial_url_pattern = SITE_URL + '{href}/seasons'
    download_url_pattern = SITE_URL + '/v_search.php?a={code}'
    season_url_pattern = SITE_URL + '{href}/season_{season}'
    episode_url_pattern = SITE_URL + '{href}/season_{season}/episode_{episode}/'
    additional_url_pattern = SITE_URL + '{href}/additional/episode_{episode}/'
    new_url_pattern = SITE_URL + '/new/page_{page}/type_{type}'

    additional_season = 999
    all_episodes = 999
    peer_id = '-PC0001-' + ''.join([str(randint(0, 9)) for _ in range(12)])

    datetime_format = '%d.%m.%Y'
    units_dict = {"ТБ": "TB", "ГБ": "GB", "МБ": "MB", "КБ": "KB", "Б": "B"}

    def __init__(self, output=True):
        self.output = output
        self.session = Session()
        
    def search(self, what, cat='all'):
        self.torrents_count = 0

        logger.info(what)

        if not self.session.is_actual: 
            self.pretty_printer({
                'link': 'Error',
                'name': self.session.error,
                'size': "0",
                'seeds': -1,
                'leech': -1,
                'engine_url': self.url,
                'desc_link': self.url
            })

            return False

        self.prevs = {}
        self.old_seasons = {}

        if parse.unquote(what).startswith('@'): 
            params = parse.unquote(what)[1:].split(':')
            
            if params:
                if params[0] == 'fav':
                    self.get_fav()

                elif params[0] == 'new':
                    if len(params) == 1:
                        self.get_new()

                    elif len(params) == 2 and params[1] == 'fav':
                        self.get_new(fav=True)
        else:
            try:
                url = self.search_url_pattern.format(what=request.quote(what))
                search_result = self.session.request(url)
            except Exception as exp:
                logger.error(exp)

            else:
                serials_tags = Parser(search_result).find_all('div', {'class': 'row-search'})
                if serials_tags:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        for serial_href in (serial.a['href'] for serial in serials_tags):
                            logger.debug(serial_href)

                            executor.submit(self.get_episodes, serial_href)
        
        logger.info('%s torrents', self.torrents_count)

    def get_new(self, fav=False, days=7):
        type = 99 if fav else 0
        today = datetime.now().date()
        self.dates = {}

        with concurrent.futures.ThreadPoolExecutor() as executor:
            page_number = 1
            while True:
                url = self.new_url_pattern.format(page=page_number, type=type)
                page = self.session.request(url)

                rows = Parser(page).find_all('div', {'class': 'row'})

                if not rows:
                    break

                for row in rows:
                    
                    release_date_str = row.find_all('div', {'class': 'alpha'})[1].text
                    release_date_str = re.search(r'\d{2}.\d{2}.\d{4}', release_date_str)[0]
                    release_date = datetime.strptime(release_date_str, self.datetime_format).date()

                    date_delta = today - release_date

                    if date_delta.days > days:
                        return

                    href = '/'.join(row.a['href'].split('/')[:3])

                    haveseen_btn = row.find('div', {'onclick': 'markEpisodeAsWatched(this);'})
                    episode_code = haveseen_btn['data-episode'].rjust(9, '0')

                    self.dates[episode_code] = release_date_str
                    
                    executor.submit(self.get_torrents, href, episode_code, True)
                
                page_number += 1

    def get_fav(self):
        page = self.session.request(SITE_URL + '/my/type_1')

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for serial in Parser(page).find_all('div', {'class': 'serial-box'}):
                href = serial.find('a', {'class': 'body'})['href']
                executor.submit(self.get_episodes, href)

    def get_episodes(self, serial_href):
        self.prevs[serial_href] = []
        self.old_seasons[serial_href] = 0

        serial_page = self.session.request(self.serial_url_pattern.format(href=serial_href))
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for button in Parser(serial_page).find_all('div', {'class': 'external-btn'}):
                item_button = button.attrs.get('onclick')

                if item_button:
                    episode_code = re.search(r'\d{7,9}', item_button)[0].rjust(9, '0')
                    logger.debug('episode_code = %s', episode_code)
                    executor.submit(self.get_torrents, serial_href, episode_code)

    def get_torrents(self, href, code, new_episodes=False):
        season, episode = int(code[3:6]), int(code[6:])
        
        if not any((
			season > self.old_seasons.get(href, -1),
			episode == self.all_episodes,
			season == self.additional_season,
			new_episodes
        )):
            return

        redir_page = self.session.request(self.download_url_pattern.format(code=code))
        torrent_page_url = re.search(r'(?<=location.replace\(").+(?="\);)', redir_page)

        if not torrent_page_url:
            return
        
        torrent_page = self.session.request(torrent_page_url[0])
        date = ' [' + self.dates.pop(code, '') + ']' if new_episodes else ''
        desc_link = self.get_description_url(href, code)

        logger.debug('desc_link = %s', desc_link)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for torrent_tag in Parser(torrent_page).find_all('div', {'class': 'inner-box--item'}):
                main = torrent_tag.find('div', {'class': 'inner-box--link main'}).a
                link, name = main['href'], main.text.replace('\n', ' ') + date
                desc_box_text = torrent_tag.find('div', {'class': 'inner-box--desc'}).text
                size, unit = re.search(r'\d+.\d+ \w\w(?=\.)', desc_box_text)[0].split()

                if not new_episodes:
                    if link in self.prevs[href]:
                        self.old_seasons[href] = max(self.old_seasons[href], season)
                        break
                    
                    self.prevs[href].append(link)
                
                torrent_dict = {
                    'link': link,
                    'name': name,
                    'size': ' '.join((size, self.units_dict.get(unit, ''))),
                    'seeds': -1,
                    'leech': -1,
                    'engine_url': self.url,
                    'desc_link': desc_link
                }

                if ENABLE_PEERS_INFO:
                    future = executor.submit(self.get_torrent_info, torrent_dict)
                    future.add_done_callback(lambda f: self.pretty_printer(f.result()))
                else:
                    self.pretty_printer(torrent_dict)

    def get_description_url(self, href, code):
        season, episode = int(code[3:6]), int(code[6:])

        if season == self.additional_season:
            return self.additional_url_pattern.format(href=href, episode=episode)

        elif episode == self.all_episodes:
            return self.season_url_pattern.format(href=href, season=season)

        else:
            return self.episode_url_pattern.format(href=href, season=season, episode=episode)

    def get_torrent_info(self, tdict):
        try:
            response = self.session.request(tdict['link'], decode=False)
        except Exception as e:
            logger.error('torrent download: %s', e)
            return tdict

        torrent = bdecode(response)
        info_hash = hashlib.sha1(bencode(torrent[b'info'])).digest()

        logger.debug('infohash = %s', info_hash)

        params = {
            'peer_id': self.peer_id,
            'info_hash': info_hash,
            'port': 6881,
            'left': 200075,
            'downloaded': 0,
            'uploaded': 0,
            'compact': 1
        }

        try:
            url = torrent[b'announce'].decode('utf-8') + '?' + parse.urlencode(params)
            response = self.session.request(url, decode=False)
        except Exception as e:
            logger.error('peers info request: %s', e)
            return tdict

        data = bdecode(response)

        tdict['seeds'] = data.get(b'complete', -1)
        tdict['leech'] = data.get(b'incomplete', 0) - 1

        return tdict
    
    def pretty_printer(self, dictionary):
        data = json.dumps(dictionary, sort_keys=True, indent=4)
        if dictionary['link'] == 'Error':
            logger.error(data)
        else:
            logger.debug(data)
            self.torrents_count += 1

        if self.output:
            prettyPrinter(dictionary)


class Session:
    site_name = 'lostfilm'
    file_name = 'lostfilm.json'
    datetime_format = '%m-%d-%y %H:%M:%S'

    token = None
    time = None
    _error = None

    @property
    def error(self):
        return 'Error: {info}.'.format(info=self._error)

    @property
    def file_path(self):
        """path to file with session data"""
        return os.path.join(STORAGE, self.file_name)

    @property
    def is_actual(self):
        """Checks the relevance of the token"""

        if self.token and self.time and not self._error:
            delta = datetime.now() - self.time
            return delta.days < 1

        return False

    @property
    def cookies(self):
        if not self.is_actual:
            self.create_new()

        return {'lf_session': self.token}

    def __init__(self):
        self.load_data()
            
        if not self.is_actual:
            if self.create_new():
                self.save_data()

    def request(self, url, params=None, decode=True):
        args = [url]

        try:
            if proxy['enable'] and self.site_name in url:
                opener = request.build_opener(
                    request.ProxyBasicAuthHandler(),
                    request.ProxyHandler(proxy['proxy_urls'])
                )

                logger.info('proxy used for "%s"', url)
            else:
                opener = request.build_opener()

            # use cookies only for lostfilm site urls
            if self.site_name in url:
                if not params:
                    params = self.cookies
                else:
                    params.update(self.cookies)

            if params:
                args.append(parse.urlencode(params).encode('utf-8'))

            result = opener.open(*args).read()

            return result if not decode else result.decode('utf-8')

        except Exception as e:
            logger.error('%s url="%s" params="%s"' % (e, url, params))

    def load_data(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, 'r') as file:
            result = json.load(file)

        if result.get('token') and result.get('time'):
            self.token = result['token']
            self.time = self.datetime_from_string(result['time'])

            logger.info('%s %s', self.token, self.time)

    def create_new(self):
        self._error = None

        if not (EMAIL and PASSWORD):
            self._error = 'Incorrect login data'
            logger.error(self._error)
            return False

        login_data = {
            "act": "users",
            "type": "login",
            "mail": EMAIL,
            "pass": PASSWORD,
            "need_captcha": "",
            "captcha": "",
            "rem": 1
        }
        
        url = SITE_URL + '/ajaxik.php?'
        params = parse.urlencode(login_data).encode('utf-8')
        
        cjar = CookieJar()
        if proxy['enable']:
            opener = request.build_opener(
                request.ProxyHandler(proxy['proxy_urls']),
                request.HTTPCookieProcessor(cjar)
            )
            logger.debug('proxy used')
        else:
            opener = request.build_opener(request.HTTPCookieProcessor(cjar))

        try:
            response = opener.open(url, params).read().decode('utf-8')
        except Exception as e:
            self._error = 'Connection failed'
            logger.error('%s %s', self._error, e)
            return False

        result = json.loads(response)
        
        if 'error' in result:
            self._error = 'Incorrect login data'

        elif 'need_captcha' in result:
            self._error = 'Captcha requested'

        else:
            for cookie in cjar:
                if cookie.name == 'lf_session':
                    self.time = datetime.now()
                    self.token = cookie.value
                    
                    logger.info('%s %s', self.token, self.time)

                    return True

            else:
                self._error = 'Token problem'

        logger.error(self._error)

        return False

    def save_data(self):
        data = {
            "token": self.token,
            "time": None if not self.time else self.datetime_to_string(self.time)
        }

        logger.info(data)

        with open(self.file_path, 'w') as file:
            json.dump(data, file)

    def datetime_to_string(self, dt_obj):
        if isinstance(dt_obj, datetime):
            return dt_obj.strftime(self.datetime_format)

        else:
            raise TypeError('argument must be datetime, not %s' % (type(dt_obj)))

    def datetime_from_string(self, dt_string):
        if isinstance(dt_string, str):
            return datetime.strptime(dt_string, self.datetime_format)

        else:
            raise TypeError('argument must be str, not %s' % (type(dt_string)))


class Tag:
    def __init__(self, tag=None, attrs=(), is_self_closing=None):
        self.type = tag
        self.is_self_closing = is_self_closing
        self._attrs = tuple(attrs)
        self._content = tuple()
        
    @property
    def attrs(self):
        """returns dict of Tag's attrs"""
        return dict(self._attrs)

    @property
    def text(self):
        """returns str of all contained text"""
        return ''.join(c if isinstance(c, str) else c.text for c in self._content)

    def _add_content(self, obj):
        if isinstance(obj, (Tag, str)):
            self._content += (obj,)
        else:
            raise TypeError('Argument must be str or %s, not %s' % (self.__class__, obj.__class__))

    def find(self, tag=None, attrs=None):
        """returns Tag or None"""

        return next(self._find_all(tag, attrs), None)

    def find_all(self, tag=None, attrs=None):
        """returns list"""

        return list(self._find_all(tag, attrs))
        
    def _find_all(self, tag_type=None, attrs=None):
        """returns generator"""

        if not (isinstance(tag_type, (str, Tag)) or tag_type is None):
            raise TypeError('tag_type argument must be str or Tag, not %s' % (tag_type.__class__))

        if not (isinstance(attrs, dict) or attrs is None):
            raise TypeError('attrs argument must be dict, not %s' % (self.__class__))

        # get tags-descendants generator
        results = self.descendants

        # filter by Tag.type
        if tag_type:
            if isinstance(tag_type, Tag):
                tag_type, attrs = tag_type.type, (attrs if attrs else tag_type.attrs)

            results = filter(lambda t: t.type == tag_type, results)

        # filter by Tag.attrs
        if attrs:
            # remove Tags without attrs
            results = filter(lambda t: t._attrs, results)

            def filter_func(tag):
                for key in attrs.keys():
                    if attrs[key] not in tag.attrs.get(key, ()):
                        return False
                return True
            
            # filter by attrs
            results = filter(filter_func, results)
        
        yield from results

    @property
    def children(self):
        """returns generator of tags-children"""

        return (obj for obj in self._content if isinstance(obj, Tag))

    @property
    def descendants(self):
        """returns generator of tags-descendants"""

        for child_tag in self.children:
            yield child_tag
            yield from child_tag.descendants

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, attr):
        if not attr.startswith("__"):
            return self.find(tag=attr)

    def __repr__(self):
        attrs = ' '.join(str(k) if v is None else '{}="{}"'.format(k, v) for k, v in self._attrs)
        starttag = ' '.join((self.type, attrs)) if attrs else self.type

        if self.is_self_closing:
            return '<{}>\n'.format(starttag)
        else:
            nested = '\n' * bool(next(self.children, None)) + ''.join(map(str, self._content))
            return '<{}>{}</{}>\n'.format(starttag, nested, self.type)

            
class Parser(HTMLParser):
    def __init__(self, html_code, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._root = Tag('_root')
        self._path = [self._root]
        
        self.feed(''.join(map(str.strip, html_code.splitlines())))
        self.handle_endtag(self._root.type)
        self.close()

        self.find = self._root.find
        self.find_all = self._root.find_all

    @property
    def attrs(self):
        return self._root.attrs

    @property
    def text(self):
        return self._root.text

    def handle_starttag(self, tag, attrs):
        self._path.append(Tag(tag=tag, attrs=attrs))

    def handle_endtag(self, tag_type):
        for pos, tag in tuple(enumerate(self._path))[::-1]:
            if isinstance(tag, Tag) and tag.type == tag_type and tag.is_self_closing is None:
                tag.is_self_closing = False

                for obj in self._path[pos + 1:]:
                    if isinstance(obj, Tag) and obj.is_self_closing is None:
                        obj.is_self_closing = True

                    tag._add_content(obj)

                self._path = self._path[:pos + 1]

                break

    def handle_startendtag(self, tag, attrs):
        self._path.append(Tag(tag=tag, attrs=attrs, is_self_closing=True))

    def handle_decl(self, decl):
        self._path.append(Tag(tag='!'+decl, is_self_closing=True))

    def handle_data(self, text):
        self._path.append(text)

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, attr):
        if not attr.startswith("__"):
            return getattr(self._root, attr)

    def __repr__(self):
        return ''.join(str(c) for c in self._root._content)


def bencode(value):
    if isinstance(value, dict):
        return b'd%be' % b''.join([bencode(k) + bencode(v) for k, v in value.items()])
    if isinstance(value, list) or isinstance(value, tuple):
        return b'l%be' % b''.join([bencode(v) for v in value])
    if isinstance(value, int):
        return b'i%ie' % value
    if isinstance(value, bytes):
        return b'%i:%b' % (len(value), value)

    raise ValueError("Only int, bytes, list or dict can be encoded, got %s" % type(value).__name__)


def bdecode(data):
    class InvalidBencode(Exception):
        @classmethod
        def at_position(cls, error, position):
            logger.error("%s at position %i" % (error, position))
            return cls("%s at position %i" % (error, position))

        @classmethod
        def eof(cls):
            logger.error("EOF reached while parsing")
            return cls("EOF reached while parsing")
            
    def decode_from_io(f):
        char = f.read(1)
        if char == b'd':
            dict_ = OrderedDict()
            while True:
                position = f.tell()
                char = f.read(1)
                if char == b'e':
                    return dict_
                if char == b'':
                    raise InvalidBencode.eof()

                f.seek(position)
                key = decode_from_io(f)
                dict_[key] = decode_from_io(f)

        if char == b'l':
            list_ = []
            while True:
                position = f.tell()
                char = f.read(1)
                if char == b'e':
                    return list_
                if char == b'':
                    raise InvalidBencode.eof()
                f.seek(position)
                list_.append(decode_from_io(f))

        if char == b'i':
            digits = b''
            while True:
                char = f.read(1)
                if char == b'e':
                    break
                if char == b'':
                    raise InvalidBencode.eof()
                if not char.isdigit():
                    raise InvalidBencode.at_position('Expected int, got %s' % str(char), f.tell())
                digits += char
            return int(digits)

        if char.isdigit():
            digits = char
            while True:
                char = f.read(1)
                if char == b':':
                    break
                if char == b'':
                    raise InvalidBencode
                digits += char
            length = int(digits)
            string = f.read(length)
            return string

        raise InvalidBencode.at_position('Unknown type : %s' % char, f.tell())

    return decode_from_io(BytesIO(data))


if __name__ == '__main__':
    import sys
    
    if 1 < len(sys.argv) < 4:

        if len(sys.argv) == 3:
            if sys.argv[1] == '-d':
                logger.setLevel(logging.DEBUG)
            
            else:
                print('%s [-d] "search query"' % (__file__))
                exit()
        else:
            logger.setLevel(logging.INFO)
        
        lostfilm().search(sys.argv[-1])
