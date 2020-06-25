#VERSION: 0.11
#AUTHORS: Bugsbringer (dastins193@gmail.com)

import concurrent.futures
import re
from html.parser import HTMLParser
from urllib import parse

from helpers import retrieve_url
from novaprinter import prettyPrinter


class darklibria:
    url = 'https://dark-libria.it/'
    name = 'dark-libria'
    supported_categories = {'all': '0'}

    units_dict = {"Тб": "TB", "Гб": "GB", "Мб": "MB", "Кб": "KB"}

    page_search_url_pattern = 'https://dark-libria.it/search?page={page}&find={what}'

    def search(self, what, cat='all'):
        what = parse.quote(parse.unquote(what))

        with concurrent.futures.ThreadPoolExecutor() as executor:
            for page in range(2, self.handle_page(what, 1) + 1):
                executor.submit(self.handle_page, what, page)

    def handle_page(self, what, page):
        html_code = retrieve_url(self.page_search_url_pattern.format(page=page, what=what))

        parser = Parser(html_code)

        torrents_table = parser.find('div', {'id': 'torrents_table'}).tbody

        for torrent in torrents_table.find_all('tr', {'class': 'torrent'}):
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

                prettyPrinter({
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


class Tag:
    def __init__(self, tag_type, *attrs):
        self.text = ''
        self.type = tag_type
        self.attrs = {attr: value for attr, value in attrs} if attrs else dict()
        self.tags = dict()

    def _add_subtag(self, subtag):
        self.tags[subtag.type] = self.tags.get(subtag.type, []) + [subtag]

    def find(self, tag_type, attrs=None):
        result = self.find_all(tag_type, attrs)
        
        return None if not result else result[0]

    def find_all(self, tag_type, attrs=None):
        result = self.tags.get(tag_type)

        if attrs and result:
            def func(tag):
                if not set(attrs.keys()) <= set(tag.attrs.keys()):
                    return False

                for attr in attrs.keys():
                    if not set(attrs[attr].split()) <= set(tag.attrs[attr].split()):
                        return False
                
                return True

            result = list(filter(func, result))

        return result

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, tag):
        return self.find(tag)


class Parser(HTMLParser):

    @property
    def text(self):
        return self._root.text

    @property
    def attrs(self):
        return self._root.attrs

    def __init__(self, html_code, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._root = Tag('_root')
        self._current_path = [self._root]

        self.feed(html_code)

    def handle_starttag(self, tag, attrs):
        new = Tag(tag, *attrs)

        for tag in self._current_path:
            tag._add_subtag(new)

        self._current_path.append(new)

    def handle_endtag(self, tag):
        self._current_path.pop()

    def handle_startendtag(self, tag, attrs):
        new = Tag(tag, *attrs)
        for tag in self._current_path:
            tag._add_subtag(new)

    def handle_decl(self, decl):
        self._root._add_subtag(Tag('declaration'))

    def handle_data(self, data):
        for tag in self._current_path:
            tag.text += data

    def find(self, tag_type, attrs=None):
        return self._root.find(tag_type, attrs)

    def find_all(self, tag_type, attrs=None):
        return self._root.find_all(tag_type, attrs)

    def __getitem__(self, key):
        return self.attrs[key]

    def __getattr__(self, tag):
        return self.find(tag)


if __name__ == '__main__':
    import sys
    
    darklibria().search(' '.join(sys.argv[1:]))
