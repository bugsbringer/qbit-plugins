#VERSION: 0.11
#AUTHORS: Bugsbringer (dastins193@gmail.com)

import concurrent.futures
from json import dumps
import logging
import os
import re
from html.parser import HTMLParser
from urllib import parse

from helpers import retrieve_url
from novaprinter import prettyPrinter

STORAGE = os.path.abspath(os.path.dirname(__file__))

LOG_FORMAT = '[%(asctime)s] %(levelname)s:%(name)s:%(funcName)s - %(message)s'
LOG_DT_FORMAT = '%d-%b-%y %H:%M:%S'

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG', format=LOG_FORMAT, datefmt=LOG_DT_FORMAT)
else:
    logging.basicConfig(level='ERROR', filename=os.path.join(STORAGE, 'darklibria.log'), format=LOG_FORMAT, datefmt=LOG_DT_FORMAT)

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

        pages_count = self.handle_page(what, 1)
        logger.info('%s pages', pages_count)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for page in range(2, pages_count + 1):
                executor.submit(self.handle_page, what, page)

        logger.info('%s torrents', self.torrents_count)

    def handle_page(self, what, page):
        parser = Parser(retrieve_url(self.page_search_url_pattern.format(page=page, what=what)))

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
            pages_div = parser.find('div', {'class': 'bg-dark d-sm-block d-none'})
            pages_count = re.search(r'(?<=page=)\d+', pages_div.find_all('li')[-1].a['href'])[0]
            return int(pages_count)

    def pretty_printer(self, dictionary):
        if __name__ == '__main__':
            data = dumps(dictionary, sort_keys=True, indent=4)
            if dictionary['link'] == 'Error':
                logger.error(data)
            else:
                logger.debug(data)
            
        else:
            prettyPrinter(dictionary)
        
        self.torrents_count += 1

class Tag:
    def __init__(self, tag_type=None, attrs=None, is_self_closing=None, root=False, parent=None, is_decl=False):
        self.children = tuple()

        self.type = tag_type
        self._attrs = attrs
        self.parent = parent

        self.is_self_closing = is_self_closing
        self.root = root
        self.is_decl = is_decl
        
    @property
    def attrs(self):
        return {} if not self._attrs else dict(self._attrs)

    @property
    def text(self):
        """returns str"""
        return ''.join(c if isinstance(c, str) else c.text for c in self.children)

    def _add_child(self, child):
        if isinstance(child, Tag):
            self._add_childtag(child)
        elif isinstance(child, str):
            self._add_text(child)
        else:
            TypeError('Argument must be str or %s, not %s' % (type(self), type(child)))

    def _add_childtag(self, child):
        if isinstance(child, Tag):
            self.children += (child, )
            child.parent = self
        else:
            TypeError('Argument must be %s, not %s' % (type(self), type(child)))

    def _add_text(self, text):
        if isinstance(text, str):
            self.children += (text, )
        else:
            TypeError('Argument must be str, not %s' % (type(text)))
        
    def _subtags(self):
        """returns list"""
        return list(filter(lambda obj: isinstance(obj, Tag), self.children))

    def _all_subtags(self):
        """returns list"""
        tags = []
        for child_tag in self._subtags():
            tags.append(child_tag)
            tags.extend(child_tag._all_subtags())
        
        return tags

    def find(self, tag_type=None, attrs=None):
        """returns Tag or None"""
        result = self.find_all(tag_type, attrs)
        return None if not result else result[0]

    def find_all(self, tag_type=None, attrs=None):
        """returns list"""
        if tag_type is None:
            results = self._all_subtags()
        else:
            results = list(filter(lambda t: t.type == tag_type, self._all_subtags()))

        if not attrs:
            return results

        def func(tag):
            if not tag.attrs or not set(attrs.keys()) <= set(tag.attrs.keys()):
                return False

            for attr in attrs.keys():
                if not set(attrs[attr].split()) <= set(tag.attrs[attr].split()):
                    return False
            
            return True

        return list(filter(func, results))

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, attr):
        return self.find(tag_type=attr)

    def __repr__(self):
        attrs = ' '.join(
            (str(attr) if value is None else '{}="{}"'.format(attr, value))
            for attr, value in self.attrs.items()
        )

        starttag = ' '.join((self.type, attrs)) if attrs else self.type

        if self.is_self_closing:
            return '<{starttag}/>'.format(starttag=starttag)
        elif self.is_decl:
            return '<!{decl}>'.format(decl=self.type)
        else:
            nested = ''.join(map(str, self.children))
            return '<{starttag}>{nested}</{tag}>'.format(starttag=starttag, nested=nested, tag=self.type)

            
class Parser(HTMLParser):
    def __init__(self, html_code, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._root = Tag('_root')
        self._path = [self._root]

        self.feed(html_code)
        for obj in self._path[1:]:
            self._root._add_child(obj)

        del self._path

        self.find = self._root.find
        self.find_all = self._root.find_all

    @property
    def attrs(self):
        return self._root.attrs

    @property
    def text(self):
        return self._root.text

    def handle_starttag(self, tag_type, attrs):
        self._path.append(Tag(tag_type=tag_type, attrs=attrs))

    def handle_endtag(self, tag_type):
        for pos, tag in tuple(enumerate(self._path))[::-1]:
            if isinstance(tag, Tag) and tag.type == tag_type and tag.is_self_closing == None:
                tag.is_self_closing = False

                for obj in self._path[pos + 1:]:
                    if isinstance(obj, Tag):
                        if obj.is_self_closing is None:
                            obj.is_self_closing = True

                    tag._add_child(obj)

                self._path = self._path[:pos + 1]
                break

    def handle_startendtag(self, tag_type, attrs):
        self._path.append(Tag(tag_type=tag_type, attrs=attrs, is_self_closing=True))

    def handle_decl(self, decl):
        self.decl = Tag(tag_type=decl, is_decl=True)
        self._path.append(self.decl)

    def handle_data(self, text):
        self._path.append(text)

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, attr):
        return self.find(tag_type=attr)

    def __repr__(self):
        return ''.join(str(c) for c in self._root.children)


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
