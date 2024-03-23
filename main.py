from bs4 import BeautifulSoup
from selenium import webdriver
import time
# from selenium.webdriver.chrome.service import Service
import re
import csv
import telebot


"""
Парсер торговой площидки Avito, с помощью Selenium
Для работоспособности не забудьте скачать сам драйвер, под свою версию браузера Chrome.
По всем возникшим вопросам, можете писать в группу https://vk.com/happython
Ссылка на статью: None
Отзывы, предложения, советы приветствуются.
"""


def getPagesCount(html):
    """определяем количеоств страниц выдачи"""
    soup = BeautifulSoup(html, 'html.parser')

    # todo: бага, может не быть страниц в целом
    pages = 1
    kek = soup.find('div', class_=re.compile('pagination-pagination'))
    if kek is not None:
        lol = kek.find_all('span', class_=re.compile('styles-module-text'))
        if lol is not None and len(lol) > 1:
            pages = lol[-1].text
    # pages = \

    print(f'Найдено страниц выдачи: {pages}')
    return int(pages)


class ApartItem(object):
    def __init__(self, name, price, geo, url):
        self.name = name
        self.price = price
        self.geo = geo
        self.url = url

    def __repr__(self):
        return "%s\n%s\n%s\n%s" % (self.price, self.name, self.geo, self.url)

    def __eq__(self, other):
        if isinstance(other, ApartItem):
            return self.url == other.url
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.url)


"""Функция сбора данных"""
def getPageContent(html):
    soup = BeautifulSoup(html, 'html.parser')
    # pages = soup.find('div', class_=re.compile('items-items')).find_all(attrs={'data-marker': "item"})[-2].text
    blocks = soup.find_all('div', class_=re.compile('iva-item-content'))
    # сбор данных с страницы
    apartmentsList = set()
    for block in blocks:
        try:
            apart = ApartItem(
                name=block.find('div', class_=re.compile('iva-item-title'))
                .find('h3').get_text(strip=True, separator=', ').replace(u'\xa0', u' '),
                price=int(block.find('div', class_=re.compile('iva-item-price'))
                .find(attrs={'itemprop': 'price'})['content']),
                geo=block.find('div', class_=re.compile('geo-root'))
                .get_text(strip=True, separator=', ').replace(u'\xa0', u' '),
                url='https://www.avito.ru'
                    + block.find('div', class_=re.compile('iva-item-title'))
                .find('a', href=True)['href'].replace(u'\xa0', u' '),
                )
            if any(x in apart.geo for x in ['Линей', 'Кропотк', 'Галуща',
                                            'Балаки', 'Красный', 'Дуси', 'Нарым']):
                apartmentsList.add(apart)
        except Exception as ex:
            print(f'Не предвиденная ошибка: {ex}')
    return apartmentsList


"""Основная функция, сам парсер"""
def parseUrlBySelenium(url: str):
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.cache.disk.enable", False)
    profile.set_preference("browser.cache.memory.enable", False)
    profile.set_preference("browser.cache.offline.enable", False)
    profile.set_preference("network.http.use-cache", False)
    # options = webdriver.ChromeOptions()
    options = webdriver.FirefoxOptions()
    # options.profile = profile
    options.add_argument("user-agent=Mozilla/5.0")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('--log-level=3')
    options.add_argument("--headless")  #режим без запуска браузера

    try:
        # укажите путь до драйвера
        # service = Service(executable_path="chromedriver")
        service = webdriver.FirefoxService()
        # browser = webdriver.Chrome(service=service, options=options)
        browser = webdriver.Firefox(service=service, options=options)
        browser.get(url)
        html = browser.page_source
        apartments = getPageContent(html)
        pages = getPagesCount(html)  #определяем количество страниц выдачи
        print(f'Парсинг страницы {1} завершен. Собрано {len(apartments)} позиций')
        # for page in range(2, 2 + 1):
        for page in range(2, pages + 1):
            link = url + f'&p={page}'
            browser.get(link)
            time.sleep(1)
            html = browser.page_source
            newAparts = getPageContent(html)
            print(f'Парсинг страницы {page} завершен. Собрано {len(newAparts)} позиций')
            apartments = apartments.union(newAparts)
    except Exception as ex:     # exception - исключение
        print(f'Не предвиденная ошибка: {ex}')
    finally:
        browser.close()
        browser.quit()

    print('Сбор данных завершен.')
    return apartments


def getDiffFromDB(hotAvitoApartments: set):
    fieldnames = ['name', 'price', 'geo', 'url']

    apartmentsDB = set()
    with open("apartments.csv", encoding='utf-8') as r_file:
        file_reader = csv.DictReader(r_file, delimiter=",", fieldnames=fieldnames)
        count = 0
        for row in file_reader:
            if count == 0:  # первая строка название полей
                count += 1
                continue
            apartmentsDB.add(ApartItem(name=row['name'], price=row['price'],
                                       geo=row['geo'], url=row['url']))

    return hotAvitoApartments - apartmentsDB


def saveToDB(apartNew: set):
    fieldnames = ['name', 'price', 'geo', 'url']
    with open("apartments.csv", mode="a", encoding='utf-8') as w_file:
        file_writer = csv.DictWriter(w_file, delimiter=",", lineterminator="\n", fieldnames=fieldnames)
        # file_writer.writerow(["name", "geo", "url"])
        # file_writer.writeheader()
        for ap in apartNew:
            file_writer.writerow({'name': ap.name,
                                  'price': ap.price,
                                  'geo': ap.geo,
                                  'url': ap.url})


def getNewRooms():
    avitoUrl = 'https://www.avito.ru/novosibirsk/kvartiry/sdam/na_dlitelnyy_srok-ASgBAgICAkSSA8gQ8AeQUg?district=805'
    print('Запуск парсера...')
    apartmentsAvito = parseUrlBySelenium(avitoUrl)
    apartNew = getDiffFromDB(apartmentsAvito)

    for ap in apartNew:
        print(ap)

    saveToDB(apartNew)

    return apartNew


def get_text_messages(message):

    # aparts = getNewRooms()
    # for ap in aparts:
    #     bot.send_message(message.from_user.id, str(ap))

    print(message.chat.id)

    pass


if __name__ == "__main__":
    # Заельцовский

    tokenStr = '6664088712:AAFeZs-HX5K_ekXquitkyanHZYnbeM5FYiU'
    bot = telebot.TeleBot(tokenStr)
    bot.register_message_handler(get_text_messages, content_types=['text'])

    while True:
        aparts = getNewRooms()
        for ap in aparts:
            # bot.send_message(-4000312952, str(ap))    # group of Apartments
            bot.send_message(460621273, str(ap))    # me
        time.sleep(60 * 30)     # every half hour

    # bot.polling(none_stop=True, interval=0)


