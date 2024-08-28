# Импортируем необходимые модули и функции
from flask import Flask, render_template, request, redirect, send_file, url_for
import requests
from io import BytesIO

# Создаем экземпляр Flask-приложения
app = Flask(__name__)

# URL для доступа к публичным ресурсам на Яндекс.Диске
YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"

# Словарь для сопоставления типов файлов с их русскими названиями
FILE_TYPES = {
    'all': 'Все',
    'image': 'Изображения',
    'document': 'Документы',
    'audio': 'Аудио',
    'video': 'Видео'
}

# Словарь для сопоставления типов файлов с MIME-типами
MIME_TYPES = {
    'image': ['image/jpeg', 'image/png', 'image/gif'],
    'document': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'audio': ['audio/mpeg', 'audio/x-wav'],
    'video': ['video/mp4', 'video/x-matroska']
}

# Функция для получения списка файлов из публичной папки Яндекс.Диска
def get_files_from_yandex_disk(public_key: str, file_type: str = 'all'):
    # Параметры для запроса к API Яндекс.Диска
    params = {'public_key': public_key}
    # Отправляем GET-запрос к API Яндекс.Диска
    response = requests.get(YANDEX_DISK_API_URL, params=params)
    if response.status_code == 200:
        # Получаем список файлов из ответа
        files = response.json()['_embedded']['items']
        # Фильтруем файлы по типу, если указан конкретный тип
        if file_type != 'all':
            files = [file for file in files if file['mime_type'] in MIME_TYPES[file_type]]
        return files
    return []  # Возвращаем пустой список в случае ошибки

# Функция для загрузки файла из Яндекс.Диска
def download_file_from_yandex_disk(public_key: str, path: str):
    # Параметры для получения ссылки на скачивание файла
    params = {'public_key': public_key, 'path': path}
    # Отправляем запрос на получение ссылки для скачивания
    download_link_response = requests.get(YANDEX_DISK_API_URL + '/download', params=params)
    if download_link_response.status_code == 200:
        # Получаем ссылку для скачивания из ответа
        download_link = download_link_response.json()['href']
        # Скачиваем файл по полученной ссылке
        file_response = requests.get(download_link)
        return file_response
    return None  # Возвращаем None в случае ошибки

# Основной маршрут для отображения страницы с формой
@app.route('/', methods=['GET', 'POST'])
def index():
    files = []  # Список файлов для отображения
    public_key = ""  # Публичный ключ для доступа к файлам
    selected_file_type = 'all'  # Выбранный тип файла
    if request.method == 'POST':
        # Получаем данные из формы
        public_key = request.form['public_key']
        selected_file_type = request.form.get('file_type', 'all')
        # Получаем список файлов по указанным параметрам
        files = get_files_from_yandex_disk(public_key, selected_file_type)
    # Отображаем страницу с формой и списком файлов
    return render_template('index.html', files=files, public_key=public_key, file_types=FILE_TYPES, selected_file_type=selected_file_type)

# Маршрут для скачивания одного файла
@app.route('/download', methods=['GET'])
def download():
    # Получаем публичный ключ и путь к файлу из параметров запроса
    public_key = request.args.get('public_key')
    path = request.args.get('path')
    # Загружаем файл
    file_response = download_file_from_yandex_disk(public_key, path)
    if file_response:
        # Отправляем файл клиенту
        return send_file(BytesIO(file_response.content), download_name=path.split('/')[-1], as_attachment=True)
    return redirect(url_for('index'))  # Перенаправляем на главную страницу в случае ошибки

# Маршрут для скачивания нескольких файлов
@app.route('/download_multiple', methods=['POST'])
def download_multiple():
    # Получаем публичный ключ и список путей к файлам из формы
    public_key = request.form.get('public_key')
    paths = request.form.getlist('paths')

    from zipfile import ZipFile  # Импортируем класс для работы с zip-архивами
    from io import BytesIO  # Импортируем класс для работы с потоками байтов

    zip_buffer = BytesIO()  # Создаем буфер для хранения zip-архива

    with ZipFile(zip_buffer, 'w') as zip_file:
        # Для каждого пути в списке
        for path in paths:
            # Загружаем файл
            file_response = download_file_from_yandex_disk(public_key, path)
            if file_response:
                # Добавляем файл в zip-архив
                zip_file.writestr(path.split('/')[-1], file_response.content)

    zip_buffer.seek(0)  # Перемещаем указатель на начало буфера

    # Отправляем zip-архив клиенту
    return send_file(zip_buffer, download_name="files.zip", as_attachment=True)

# Запускаем приложение Flask
if __name__ == '__main__':
    app.run(debug=True)