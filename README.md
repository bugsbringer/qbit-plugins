# qBittorrent search plugins

[Readme in russian](https://github.com/bugsbringer/qbit-plugins/blob/master/README.ru.md)

Plugins
-------

* LostFilm.TV
* dark-libria.it

Installation
------------

1.For private torrent-trackers(LostFilm):

* Save *.py file in any convenient directory
* Open this file using **notepad** or any other **text editor**
* Replace text in rows **EMAIL** and **PASSWORD** with **your login data**<br>
Example:

        EMAIL = "example123@gmail.com"
        PASSWORD = "qwerty345"

2.Follow the **official tutorial**: [Install search plugins](https://github.com/qbittorrent/search-plugins/wiki/Install-search-plugins)

LostFilm plugin features
------------------------

* Information about seeders and leechers in search results. (Reduces search speed)<br>
        You can disable this functionality in lostfilm.py file:

        ENABLE_PEERS_INFO = False

* Additional search queries:<br>
*just enter it in search field*
  * Favorites serials:

        @fav

    * New episodes in the last 7 days:

          @new

      * Among favorites:

            @new:fav

Errors
------

### Captcha requested

* You need to **logout**:
  * Go to <https://www.lostfilm.tv/my_logout>
    * Then aprove logout
* **Login** again:
  * Go to <https://www.lostfilm.tv/login>
  * Enter your login data and captcha
  * And finally Log in

### Connection failed

* Could not connect to server

### Incorrect login data

* Most likely you incorrectly filled in the authorization data
