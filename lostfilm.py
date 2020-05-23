#VERSION: 0.12
#AUTHORS: Bugsbringer (dastins193@gmail.com)


EMAIL = 'YOUR_EMAIL'
PASSWORD = 'YOUR_PASSWORD'


import concurrent.futures
import hashlib
import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from random import randint
from urllib import parse, request

from helpers import retrieve_url
from novaprinter import prettyPrinter

# bencode uses to get info from torrent file about seeders, leechers
try:
    import bencode
except ImportError:
    bencode = None

try:
    import requests
except ImportError:
    requests = None


class lostfilm(object):
    url = 'https://www.lostfilm.tv'
    name = 'LostFilm'
    supported_categories = {'all': '0'}

    search_url_pattern = 'https://www.lostfilm.tv/search/?q={what}'
    serial_url_pattern = 'https://www.lostfilm.tv{href}/seasons'
    download_url_pattern = 'https://www.lostfilm.tv/v_search.php?a={code}'
    season_url_pattern = 'https://www.lostfilm.tv{href}/season_{season}'
    episode_url_pattern = 'https://www.lostfilm.tv{href}/season_{season}/episode_{episode}/'
    additional_url_pattern = 'https://www.lostfilm.tv{href}/additional/episode_{episode}/'

    additional_season = 999
    all_episodes = 999
    peer_id = None

    def __init__(self):
        self.session = Session()

    def search(self, what, cat='all'):
        if not self.session.is_actual:
            prettyPrinter({
                'link': ' ',
                'name': 'Error: {info}'.format(info=self.session.error),
                'size': "0",
                'seeds': -1,
                'leech': -1,
                'engine_url': self.url,
                'desc_link': 'https://www.lostfilm.tv/login'
            })

            return

        self.prevs = {}
        self.old_seasons = {}

        search_result = retrieve_url(self.search_url_pattern.format(what=request.quote(what)))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for serial in Parser(search_result).find_all('div', {'class': 'row-search'}):
                executor.submit(self.handle_serial, serial.find('a')['href'])

    def handle_serial(self, href):
        self.prevs[href] = []
        self.old_seasons[href] = 0

        serial_page = retrieve_url(self.serial_url_pattern.format(href=href))

        with concurrent.futures.ThreadPoolExecutor() as executor:

            for button in Parser(serial_page).find_all('div', {'class': 'external-btn'}):
                item_button = button.attrs.get('onclick')
                
                if item_button:
                    code = re.search(r'\d{7,9}', item_button)[0].rjust(9, '0')
                    season, episode = int(code[3:6]), int(code[6:])
                    
                    if season > self.old_seasons[href] or episode == self.all_episodes or season == self.additional_season:
                        executor.submit(self.handle_torrents, href, code)

    def handle_torrents(self, href, code):
        units_dict = {"ТБ": "TB", "ГБ": "GB", "МБ": "MB", "КБ": "KB"}

        opener = request.build_opener(request.HTTPCookieProcessor(CookieJar()))
        params = parse.urlencode(self.session.cookies).encode('utf-8')
        url = self.download_url_pattern.format(code=code)
        redir_page = opener.open(url, params).read().decode('utf-8')

        torrent_page_url = re.search(r'(?<=location.replace\(").+(?="\);)', redir_page)

        if torrent_page_url:

            torrent_page = retrieve_url(torrent_page_url[0])

            for torrent_tag in Parser(torrent_page).find_all('div', {'class': 'inner-box--item'}):
                main = torrent_tag.find('div', {'class': 'inner-box--link main'}).find('a')
                link, name = main['href'], main.text.replace('\n', ' ')

                # if this url alredy handled, then all episodes of this and older
                # seasons will have torrent urls of episode's season instead of episode
                if link in self.prevs[href]:
                    self.old_seasons[href] = max(self.old_seasons[href], int(code[3:6]))
                    break

                self.prevs[href].append(link)

                size, unit = re.search(r'\d+.\d+ \w\w(?=\.)', torrent_tag.find(
                    'div', {'class': 'inner-box--desc'}).text)[0].split()
                torrent_info = self.get_torrent_info(link)

                torrent_dict = {
                    'link': link,
                    'name': name,
                    'size': ' '.join([size, units_dict.get(unit, '')]),
                    'seeds': torrent_info['seeders'],
                    'leech': torrent_info['leechers'],
                    'engine_url': self.url,
                    'desc_link': self.get_description_url(href, code)
                }

                prettyPrinter(torrent_dict)

    def get_description_url(self, href, code):
        season, episode = int(code[3:6]), int(code[6:])

        if season == self.additional_season:
            return self.additional_url_pattern.format(href=href, episode=episode)

        elif episode == self.all_episodes:
            return self.season_url_pattern.format(href=href, season=season)

        else:
            return self.episode_url_pattern.format(href=href, season=season, episode=episode)

    def get_torrent_info(self, url):
        if not bencode or not requests:
            return {"seeders": -1, "leechers": -1}

        try:
            torrent = bencode.bdecode(requests.get(url).content)
            info_hash = hashlib.sha1(bencode.bencode(torrent['info'])).digest()
            
            if not self.peer_id:
                self.peer_id = '-PC0001-' + ''.join([str(randint(0, 9)) for _ in range(12)])

            params = {
                'peer_id': self.peer_id,
                'info_hash': info_hash,
                'port': 6881,
                'left': 200075,
                'downloaded': 0,
                'uploaded': 0,
                'compact': 1
            }

            data = bencode.bdecode(requests.get(torrent['announce'], params).content)

            return {"seeders": data['complete'], "leechers": data['incomplete'] - 1}

        except:
            return {"seeders": -1, "leechers": -1}


class Session:
    storage = os.path.abspath(os.path.dirname(__file__))
    file_name = 'lostfilm.json'
    datetime_format = '%m-%d-%y %H:%M:%S'

    token = None
    time = None
    error = None

    @property
    def file_path(self):
        return os.path.join(self.storage, self.file_name)

    @property
    def is_actual(self):
        """Needs to change session's token every 24 hours ot avoid captcha"""

        if self.token and self.time:
            delta = datetime.now() - self.time
            return delta.days < 1

        else:
            return False

    @property
    def cookies(self):
        if not self.is_actual:
            self.create_new()

        return {'lf_session': self.token}

    def __init__(self):
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.file_path):
            self.create_new()
            self.save_data()

        else:
            with open(self.file_path, 'r') as file:
                result = json.load(file)

            if result.get('token') and result.get('time'):
                self.token = result['token']
                self.time = self.datetime_from_string(result['time'])

            if not self.is_actual:
                self.create_new()

    def create_new(self):
        if not EMAIL or EMAIL == "YOUR_EMAIL" or not PASSWORD or PASSWORD == 'YOUR_PASSWORD':
            self.error = 'Fill login data. {path}'.format(path=self.file_path)

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

        url = "https://www.lostfilm.tv/ajaxik.php?"
        
        cj = CookieJar()
        opener = request.build_opener(request.HTTPCookieProcessor(cj))
        params = parse.urlencode(login_data)
        response = opener.open(url, params.encode('utf-8'))
        
        result = json.loads(response.read().decode('utf-8'))
        
        if 'error' in result:
            self.error = result['error']

        elif 'need_captcha' in result:
            self.error = 'Captcha requested. Check description by right click.'

        else:
            for cookie in cj:
                if cookie.name == 'lf_session':
                    self.token = cookie.value
                    self.time = datetime.now()

                    self.save_data()

                    return True

            else:
                self.error = 'Unknown'
        
        return False

    def save_data(self):
        data = {
            "token": self.token,
            "time": None if not self.time else self.datetime_to_string(self.time)
        }

        with open(self.file_path, 'w') as file:
            json.dump(data, file)

    def datetime_to_string(self, dt_obj):
        if type(dt_obj) is datetime:
            return dt_obj.strftime(self.datetime_format)

        else:
            raise TypeError('argument must be datetime')

    def datetime_from_string(self, dt_string):
        if type(dt_string) is str:
            return datetime.strptime(dt_string, self.datetime_format)

        else:
            raise TypeError('argument must be str')


class Tag:
    text = None

    def __init__(self, tag_type, *attrs):
        self.type = tag_type
        self.attrs = {attr: value for attr, value in attrs}
        self.tags = {}

    def add(self, tag):
        if not self.tags.get(tag.type):
            self.tags[tag.type] = []

        self.tags[tag.type].append(tag)

    def find(self, tag_type, attrs=None):
        result = self.find_all(tag_type, attrs)

        return None if not result else result[0]

    def find_all(self, tag_type, attrs=None):
        result = self.tags.get(tag_type, [])

        if attrs and result:
            result = list(filter(lambda tag: set(attrs.items()) & set(tag.attrs.items()), result))

        return result

    def __getitem__(self, attr):
        return self.attrs[attr]


class Parser(HTMLParser):
    def __init__(self, html_code, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._root = Tag('doc')
        self._current_path = [self._root]

        self.feed(html_code)

    def handle_starttag(self, tag, attrs):
        new = Tag(tag, *attrs)
        
        for tag in self._current_path:
            tag.add(new)
        
        self._current_path.append(new)

    def handle_endtag(self, tag):
        self._current_path.pop()

    def handle_data(self, data):
       self._current_path[-1].text = data

    def find(self, tag_type, attrs=None):
        return self._root.find(tag_type, attrs)

    def find_all(self, tag_type, attrs=None):
        return self._root.find_all(tag_type, attrs)


if __name__ == '__main__':
    import sys

    lf = lostfilm()
    lf.search(' '.join(sys.argv[1:]))
