#VERSION: 0.12
#AUTHORS: Bugsbringer (dastins193@gmail.com)

import concurrent.futures
import logging
import os
import re
from html.parser import HTMLParser
from json import dumps
from urllib import parse

from helpers import retrieve_url
from novaprinter import prettyPrinter

STORAGE = os.path.abspath(os.path.dirname(__file__))

LOG_FORMAT = '[%(asctime)s] %(levelname)s:%(name)s:%(funcName)s - %(message)s'
LOG_DT_FORMAT = '%d-%b-%y %H:%M:%S'

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG', format=LOG_FORMAT, datefmt=LOG_DT_FORMAT)
else:
    logging.basicConfig(level='WARNING', filename=os.path.join(STORAGE, 'darklibria.log'), format=LOG_FORMAT, datefmt=LOG_DT_FORMAT)

logger = logging.getLogger('darklibria')
logger.setLevel(logging.WARNING)


class darklibria:
    url = 'https://dark-libria.it/'
    name = 'dark-libria'
    supported_categories = {'all': '0'}
    
    units_dict = {"Тб": "TB", "Гб": "GB", "Мб": "MB", "Кб": "KB", "б": "B"}
    page_search_url_pattern = 'https://dark-libria.it/search?page={page}&find={what}'

    def search(self, what, cat='all'):
        logger.info(what)

        self.torrents_count = 0
        what = parse.quote(parse.unquote(what))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for page in range(2, self.handle_page(what, 1) + 1):
                executor.submit(self.handle_page, what, page)

        logger.info('%s torrents', self.torrents_count)

    def handle_page(self, what, page):
        try:
            parser = Parser(retrieve_url(self.page_search_url_pattern.format(page=page, what=what)))
        except Exception as exp:
            logger.error(exp)
            self.pretty_printer({
                'link': 'Error',
                'name': 'Connection failed',
                'size': "0",
                'seeds': -1,
                'leech': -1,
                'engine_url': self.url,
                'desc_link': self.url
            })

            return 0

        if page == 1:
            pages_div = parser.find('div', {'class': 'bg-dark d-sm-block d-none'})
            pages_count = re.search(r'(?<=page=)\d+', pages_div.find_all('li')[-1].a['href'])[0]

            logger.info('%s pages', pages_count)

        torrents_table = parser.find('div', {'id': 'torrents_table'}).tbody
        torrents = torrents_table.find_all('tr', {'class': 'torrent'})

        logger.info('[page %s] %s animes', page, len(torrents))

        for torrent in torrents:
            name = torrent.a.span.text
            desc_link = torrent.a['href']
            
            qualities = []
            quality_cell = torrent.find('td', {'class': 'torrent d-none d-lg-table-cell'})

            for quality in quality_cell.find_all('ul', {'class': 'torrent'}):
                qualities.append(parse.unquote(quality.text))

            other_cells = torrent.find_all('td', {'class': 'torrent text-center'})
            
            episodes = []
            for episode in other_cells[0].find_all('ul', {'class': 'torrent'}):
                episodes.append(episode.text)

            sizes = []
            for size in other_cells[1].find_all('ul', {'class': 'torrent'}):
                sizes.append(parse.unquote(size.text))

            links = []
            for link in other_cells[3].find_all('ul', {'class': 'torrent'}):
                links.append(link.a['href'])
            
            seeders = []
            seeds_cell = torrent.find('td', {'class': 'torrent text-success text-center d-none d-lg-table-cell'})
            for seed in seeds_cell.find_all('ul', {'class': 'torrent'}):
                seeders.append(seed.text)

            leechers = []
            leechs_cell = torrent.find('td', {'class': 'torrent text-danger text-center d-none d-lg-table-cell'})
            for leech in leechs_cell.find_all('ul', {'class': 'torrent'}):
                leechers.append(leech.text)

            data = zip(qualities, episodes, links, sizes, seeders, leechers)

            for qual, ep, link, size, seeds, leechs in data:
                size, unit = size.split()

                self.pretty_printer({
                    'link': self.url + link,
                    'name': ' '.join((name, qual, ep)),
                    'size': size + ' ' + self.units_dict[unit],
                    'seeds': int(seeds),
                    'leech': int(leechs),
                    'engine_url': self.url,
                    'desc_link': self.url + desc_link
                })
            
        if page == 1:
            return int(pages_count)

    def pretty_printer(self, dictionary):
        data = dumps(dictionary, sort_keys=True, indent=4)
        if dictionary['link'] == 'Error':
            logger.error(data)
        else:
            logger.debug(data)

        if __name__ != '__main__':
            prettyPrinter(dictionary)
        
        self.torrents_count += 1


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
            return '<{starttag}>\n'.format(starttag=starttag)
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


if __name__ == '__main__':
    import sys
    
    if 1 < len(sys.argv) < 4:

        if len(sys.argv) == 3:
            if sys.argv[1] == '-d':
                logger.setLevel(logging.DEBUG)
            
            else:
                print('%s [-d] "search_query"' % (__file__))
                exit()
        else:
            logger.setLevel(logging.INFO)
        
        darklibria().search(sys.argv[-1])
