import requests
import json
import re
from urllib.parse import quote_plus, unquote_plus
from requests.utils import requote_uri
from warcio import ArchiveIterator
from bs4 import BeautifulSoup
import logging

# Установка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Функция для поиска по Common Crawl
def search_ru_wiki(index_name, limit=10):
    try:
        url = 'ru.wikipedia.org/*'
        encoded_url = quote_plus(url)
        index_url = f'http://index.commoncrawl.org/{index_name}-index?url={encoded_url}&output=json'
        response = requests.get(index_url)
        
        if response.status_code == 200:
            records = response.text.strip().split('\n')
            logging.info(f'Найдено {len(records)} записей в индексе {index_name}')
            return [json.loads(record) for record in records[:limit]]
        else:
            logging.error(f"Ошибка при поиске: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Ошибка в search_ru_wiki: {e}")
        return None

# Функция для загрузки и извлечения WARC-записи
def fetch_single_record(warc_record_filename, offset, length):
    try:
        s3_url = f'https://data.commoncrawl.org/{warc_record_filename}'
        byte_range = f'bytes={offset}-{offset + length - 1}'
        response = requests.get(
            s3_url,
            headers={'Range': byte_range},
            stream=True
        )

        if response.status_code == 206:
            stream = ArchiveIterator(response.raw)
            for warc_record in stream:
                if warc_record.rec_type == 'response':
                    return warc_record.content_stream().read()
        else:
            logging.error(f"Ошибка загрузки данных: {response.status_code}")
    except Exception as e:
        logging.error(f"Ошибка в fetch_single_record: {e}")
    return None

# Функция для поиска ключевых слов с регулярными выражениями для склонений
def find_keywords_in_text(text, patterns):
    found_keywords = []
    for pattern, keyword in patterns:
        # Ищем соответствие по регулярному выражению
        if re.search(pattern, text, re.IGNORECASE):
            found_keywords.append(keyword)
    return found_keywords

# Задание паттернов для склонений
patterns = [
    # Лошади
    (r'\bлошад[ьеиюям]\b', 'лошадь'),
    (r'\bкон[ныьиейямю]\b', 'конь'),
    (r'\bжереб[ецьяюеям]\b', 'жеребец'),
    (r'\bипподром[ауеоы]?\b', 'ипподром'),
    
    # Конный спорт и другие термины
    (r'\bконн[ыйаяоеые]{0,2} спорт[ауеы]?\b', 'конный спорт'),
    (r'\bконн[ые]{0,2} скачк[аиоамуеы]?\b', 'конные скачки'),
    (r'\bконкур[ауеоы]?\b', 'конкур'),
    (r'\bвыездк[ауеоы]?\b', 'выездка'),
    (r'\bтроеборь[еюяем]\b', 'троеборье')
]

# Добавим больше индексов для расширения поиска
index_names = [
    'CC-MAIN-2024-38', 'CC-MAIN-2024-33', 'CC-MAIN-2024-30', 
    'CC-MAIN-2024-26', 'CC-MAIN-2024-22', 'CC-MAIN-2024-18',
    'CC-MAIN-2024-10'
]

# Поиск по нескольким индексам
results = []
for index_name in index_names:
    index_results = search_ru_wiki(index_name, limit=100)  # Увеличим лимит до 100 записей на каждый индекс
    if index_results:
        results += index_results

# Удаление дубликатов
unique_results = {}
for result in results:
    if result['url'] not in unique_results:
        unique_results[result['url']] = result

logging.info(f"Уникальных результатов после фильтрации: {len(unique_results)}")

# Загрузка HTML данных и анализ по содержимому страниц
html_results = {}
for result in unique_results.values():
    record = fetch_single_record(result['filename'], int(result['offset']), int(result['length']))
    if record:
        html_results[result['url']] = record

# Анализ HTML страниц и вывод только тех, где найдены ключевые слова
for url, html in html_results.items():
    try:
        beautiful_soup = BeautifulSoup(html, 'html.parser')
        title = beautiful_soup.title.string if beautiful_soup.title else "Без названия"
        page_text = beautiful_soup.get_text()  # Используем полный текст страницы
        keywords_found = find_keywords_in_text(page_text, patterns)  # Ищем ключевые слова с учётом склонений
        
        # Если ключевые слова найдены, выводим название статьи, URL и ключевые слова
        if keywords_found:
            print(f"Название статьи: {title}")
            print(f"URL: {unquote_plus(url)}")
            print(f"Ключевые слова: {', '.join(keywords_found)}")
            print("\n" + "-"*50 + "\n")
    
    except Exception as e:
        logging.error(f"Ошибка при анализе HTML: {e}")










