# LostFilm.TV
### Popular Russian dubbing studio of foreign TV shows

Installation
---------------
* Save [lostfilm.py](https://raw.githubusercontent.com/bugsbringer/qbit-plugins/master/lostfilm.py) in any convenient directory
* Open this file using **notepad** or any other **text editor**
* Replace text in rows **EMAIL** and **PASSWORD** with **your login data**</br>
Example:</br>

        EMAIL = 'example123@gmail.com'
        PASSWORD = 'qwerty345'

* Then follow the **official tutorial**: [Install search plugins](https://github.com/qbittorrent/search-plugins/wiki/Install-search-plugins)

Unknown **seeders** and **leechers** in the search results
-------------------------------------------
lostfilm.tv does not provide information about seeders and leechers, but we can get it from a torrent file.</br></br>
You need to install additional python3 modules **bencode** and **requests**:

        pip install bencode.py
        pip install requests

It also slows down the search.

Errors
---------
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
