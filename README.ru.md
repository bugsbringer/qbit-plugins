 # Поисковой плагин для qBittorrent

Установка
------------
* Сохраните [lostfilm.py](https://raw.githubusercontent.com/bugsbringer/qbit-plugins/master/lostfilm.py) в любую удобную директорию
* Откройте файл при помощи **блокнота** или другого **текстового редактора**
* Замените текст в строках **EMAIL** и **PASSWORD**  **своими данными для входа на сайт**<br>
Пример:

        EMAIL = "example123@gmail.com"
        PASSWORD = "qwerty345"

* Далее следуйте **официальному руководству**: [Install search plugins](https://github.com/qbittorrent/search-plugins/wiki/Install-search-plugins)

Особенности
--------
* Информация о сидах и личах в результатах поиска. (Замедляет поиск)<br>
        Вы можете отключить эту функцию в lostfilm.py файле:

        ENABLE_PEERS_INFO = False

* Дополнительные поисковые запросы:<br>
*Просто введите в поле поиска*
    * Избранные сериалы:
        
            @fav

    * Новые эпизоды:
        * Среди всех или среди избранных(за последние 7 дней):
        
                @new
                @new:fav

Ошибки
------
### Captcha requested
* Вам нужно **выйти** из своего аккаунта на сайте:
    * Перейдите по ссылке https://www.lostfilm.tv/my_logout
    * Подтвердите выход
* **Войти** опять:
    * Перейдите по ссылке https://www.lostfilm.tv/login
    * Введи ваши данные для входа и капчу
    * Войдите :)

### Fill login data
* Похоже что поля **EMAIL** и **PASSWORD** не заполнены

### {error_code}
* Похоже что поля **EMAIL** и **PASSWORD** заполнены не верно
