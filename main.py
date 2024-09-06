import sys
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from webdriver_manager.firefox import GeckoDriverManager
# from selenium.webdriver.chrome.service import Service
import re
import csv
import telebot

GROUP_ID = -4000312952
DB_NAME = "cars.csv"

"""
Парсер торговой площидки Avito, с помощью Selenium
Для работоспособности не забудьте скачать сам драйвер, под свою версию браузера Chrome.
По всем возникшим вопросам, можете писать в группу https://vk.com/happython
Ссылка на статью: None
Отзывы, предложения, советы приветствуются.
"""


def getNextPageUrl(html) -> str:
    soup = BeautifulSoup(html, 'html.parser')

    kek = soup.find('div', { 'data-ftid' : "component_pagination" })
    if kek is not None:
        lol = kek.find('a', { 'data-ftid' : "component_pagination-item-next" })
        if lol is not None:
            href = lol['href']
            if 'all/page' in href:
                return href

    return ''


class GoodItem(object):
    def __init__(self, name, price, geo, url):
        self.name = name
        self.price = price
        self.geo = geo
        self.url = url

    def __repr__(self):
        return "%s\n%s\n%s\n%s" % (self.price, self.name, self.geo, self.url)

    def __eq__(self, other):
        if isinstance(other, GoodItem):
            return self.url == other.url
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.url)


"""Функция сбора данных"""
def getPageContent(html) -> set[GoodItem]:
    soup = BeautifulSoup(html, 'html.parser')
     #.find('div', class_=re.compile('css-1173kvb')) \
    blockSet = soup.find_all('div', { 'data-ftid' : "bulls-list_bull" })
    # сбор данных с страницы
    goodsSet = set()
    # print(f"blocks: {len(blockSet)}")
    for block in blockSet:
        try:
            # .find('div', class_=re.compile('css-jlnpz8'))
            price = block.find('span', { 'data-ftid' : "bull_price" }).get_text(strip=True, ).replace(u'\xa0', u' ')
            price = int(int(str(price).replace(' ', '')) / 1000)
            item = GoodItem(
                name=block.find('h3').get_text(strip=True, separator=', ').replace(u'\xa0', u' '),
                price=price,
                geo='',
                url=block.find('a', { 'data-ftid' : "bull_title" })['href']
                )
            
            goodsSet.add(item)
        except Exception as ex:
            print(f'Не предвиденная ошибка: {ex}')
    return goodsSet


"""Основная функция, сам парсер"""
def parseUrlBySelenium(url: str) -> set[GoodItem]:
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

    # укажите путь до драйвера
    # service = Service(executable_path="chromedriver")
    service = webdriver.FirefoxService()
    # service = webdriver.FirefoxService(executable_path="geckodriver.exe")
    # service = webdriver.FirefoxService(executable_path="C:/Users/prince/geckodriver.exe")
    # service = webdriver.FirefoxService(executable_path=GeckoDriverManager().install())
    # browser = webdriver.Chrome(service=service, options=options)
    browser = webdriver.Firefox(service=service, options=options)
    try:
        goods = set[GoodItem]()
        pageNextUrl = ''
        page = 1
        link = url
        while True:
            browser.get(link)
            html = browser.page_source
            goodsOnPage = getPageContent(html)
            pageNextUrl = getNextPageUrl(html)
            pos = pageNextUrl.find("all")
            # print(pageNextUrl[pos:pos+20])
            print(f'Парсинг страницы {page} завершен. Собрано {len(goodsOnPage)} позиций')
            goods = goods.union(goodsOnPage)

            if pageNextUrl == '':
                break

            link = pageNextUrl            
            time.sleep(1)
            page += 1

    except Exception as ex:     # exception - исключение
        print(f'Не предвиденная ошибка: {ex}')
    finally:
        browser.close()
        browser.quit()

    print('Сбор данных завершен.')
    return goods


def getDiffFromDB(hotGoods: set[GoodItem]) -> set[GoodItem]:
    fieldnames = ['name', 'price', 'geo', 'url']

    goodsDB = set()
    with open(DB_NAME, encoding='utf-8') as r_file:
        file_reader = csv.DictReader(r_file, delimiter=",", fieldnames=fieldnames)
        count = 0
        for row in file_reader:
            if count == 0:  # первая строка название полей
                count += 1
                continue
            goodsDB.add(GoodItem(name=row['name'], price=row['price'],
                                       geo=row['geo'], url=row['url']))

    return hotGoods - goodsDB


def saveToDB(apartNew: set):
    fieldnames = ['name', 'price', 'geo', 'url']
    with open(DB_NAME, mode="a", encoding='utf-8') as w_file:
        file_writer = csv.DictWriter(w_file, delimiter=",", lineterminator="\n", fieldnames=fieldnames)
        # file_writer.writerow(["name", "geo", "url"])
        # file_writer.writeheader()
        for ap in apartNew:
            file_writer.writerow({'name': ap.name,
                                  'price': ap.price,
                                  'geo': ap.geo,
                                  'url': ap.url})
    print('Save to DB successful')


def getNewRooms():
    # avitoUrl = 'https://www.avito.ru/novosibirsk/kvartiry/sdam/na_dlitelnyy_srok-ASgBAgICAkSSA8gQ8AeQUg?district=805'
    # avitoUrl = 'https://www.avito.ru/novosibirsk/koshki?cd=1&q=котята&s=1'
    url = "https://novosibirsk.drom.ru/auto/all/?frametype[]=10&frametype[]=5&frametype[]=9&frametype[]=7&distance=100&maxprice=1000000&transmission[]=2&transmission[]=3&transmission[]=4&transmission[]=5&transmission[]=-1&mv=1.0&unsold=1&maxprobeg=150000&isOwnerSells=1"
    print('Запуск парсера...')
    goodsAll = parseUrlBySelenium(url)
    goodsNew = getDiffFromDB(goodsAll)

    for good in goodsNew:
        print(good)

    saveToDB(goodsNew)

    return goodsNew


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

    # bot.polling(none_stop=True, interval=0)
    bot.send_message(-4000312952, 'hi')
    sys.exit(0)

    while True:
        goods = getNewRooms()
        for g in goods:
            bot.send_message(GROUP_ID, str(g))    # group of search elements
            time.sleep(1)
            # bot.send_message(460621273, str(ap))    # me
        print('ждёмс')
        for i in range(3):
            time.sleep(60 * 10)     # every half hour
            print(f"{i + 1}0 minutes left...")
        

    


