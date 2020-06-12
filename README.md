 # qBittorrent search plugin

This file also has [Russian translation](https://github.com/bugsbringer/qbit-plugins/blob/master/README.ru.md)

LostFilm.TV
-----------
Popular Russian dubbing studio of foreign TV shows

Installation
------------
* Save [lostfilm.py](https://raw.githubusercontent.com/bugsbringer/qbit-plugins/master/lostfilm.py) in any convenient directory
* Open this file using **notepad** or any other **text editor**
* Replace text in rows **EMAIL** and **PASSWORD** with **your login data**<br>
Example:

        EMAIL = "example123@gmail.com"
        PASSWORD = "qwerty345"

* Then follow the **official tutorial**: [Install search plugins](https://github.com/qbittorrent/search-plugins/wiki/Install-search-plugins)

Features
--------
* Information about seeders and leechers in search results. (Reduces search speed)<br>
        You can disable this functionality in lostfilm.py file:

        ENABLE_PEERS_INFO = False

* Additional search queries:<br>
*just enter it in search field*
    * Favorites serials:
        
            @fav

    * New episodes:
        * Among all or favorites in the last 7 days:
        
                @new
                @new:fav

Errors
------
### Captcha requested
* You need to **logout**:
    * Go to https://www.lostfilm.tv/my_logout
    * Then aprove logout
* **Login** again:
    * Go to https://www.lostfilm.tv/login
    * Enter your login data and captcha
    * And finally Log in 

### Fill login data
* Most likely you did not fill in the authorization data.

### {error_code}
* Most likely you incorrectly filled in the authorization data
