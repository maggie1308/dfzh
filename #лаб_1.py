
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import graphviz

# Базовый URI для API запросов Википедии
BASE_URI = 'https://ru.wikipedia.org'

# Функция для получения данных статьи по названию через API
def get_article(query: str) -> dict:
    url = f'{BASE_URI}/w/api.php?action=parse&page={quote_plus(query)}&format=json'
    response = requests.get(url)
    
    # Проверка успешности запроса
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            print(f"Ошибка обработки JSON для статьи: {query}")
            return {}
    else:
        print(f"Ошибка загрузки статьи: {query}, статус код: {response.status_code}")
        return {}

# Функция для парсинга HTML содержимого статьи
def get_parsed_html(article: dict) -> BeautifulSoup:
    if 'parse' in article and 'text' in article['parse']:
        html = article['parse']['text']['*']
        return BeautifulSoup(html, 'html.parser')
    return None

# Функция для поиска важных ссылок (всего два абзаца, первый и второй)
def find_important_links(soup: BeautifulSoup) -> list:
    links = []
    if not soup:
        return links

    content = soup.find('div', class_='mw-parser-output')
    if not content:
        return links

    # Первый абзац и второй абзац
    paragraphs = content.find_all('p', recursive=False, limit=2)
    
    for p in paragraphs:
        a_tags = p.find_all('a', href=True)
        for a in a_tags:
            href = a.get('href')
            if href.startswith('/wiki/') and not href.startswith(f'/wiki/{quote_plus("Файл")}:'):
                links.append({
                    'title': a.get('title') if a.get('title') else a.text,
                    'href': href
                })
    return links

# Функция для построения графа на языке DOT и его визуализации
def build_and_visualize_dot_graph(query: str, graph_limit: int = 30):
    graph_data = {}
    to_process = [query]
    processed = set()
    dot = graphviz.Digraph(comment='WikipediaGraph')

    while to_process and len(graph_data) < graph_limit:
        current_article = to_process.pop(0)
        
        if current_article in processed:
            continue

        print(f"Обрабатывается статья: {current_article}")
        article_data = get_article(current_article)
        soup = get_parsed_html(article_data)

        if soup:
            links = find_important_links(soup)
            graph_data[current_article] = links

            dot.node(current_article)

            for link in links:
                if link['title'] not in processed and link['title'] not in to_process:
                    to_process.append(link['title'])

                dot.edge(current_article, link['title'])

        processed.add(current_article)

    # Сохранение графа в формате DOT
    dot.save('wikipedia_graph.dot')
    print("Граф статей сохранен в файл wikipedia_graph.dot")

    # Визуализация и сохранение графа как изображения
    output_format = 'png'  # Вы можете выбрать другой формат, например, 'pdf', 'svg'
    try:
        dot.render('wikipedia_graph', format=output_format, view=True)
        print(f"Граф статей визуализирован и сохранен как изображение в формате {output_format}")
    except Exception as e:
        print(f"Ошибка при визуализации графа: {e}")
        print("Убедитесь, что Graphviz установлен и его исполняемые файлы доступны в PATH.")

# Основная программа для построения и визуализации графа
def main():
    query = input("Введите запрос: ").strip()
    
    # Построение графа статей и его визуализация, ограничение - 30 статей
    build_and_visualize_dot_graph(query)

if __name__ == '__main__':
    main()
