from flask import Flask, render_template, request, redirect, send_file, url_for
import requests
from io import BytesIO

app = Flask(__name__)

YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"

FILE_TYPES = {
    'all': 'Все',
    'image': 'Изображения',
    'document': 'Документы',
    'audio': 'Аудио',
    'video': 'Видео'
}

MIME_TYPES = {
    'image': ['image/jpeg', 'image/png', 'image/gif'],
    'document': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'audio': ['audio/mpeg', 'audio/x-wav'],
    'video': ['video/mp4', 'video/x-matroska']
}


def get_files_from_yandex_disk(public_key: str, file_type: str = 'all'):
    params = {'public_key': public_key}
    response = requests.get(YANDEX_DISK_API_URL, params=params)
    if response.status_code == 200:
        files = response.json()['_embedded']['items']
        if file_type != 'all':
            files = [file for file in files if file['mime_type'] in MIME_TYPES[file_type]]
        return files
    return []


def download_file_from_yandex_disk(public_key: str, path: str):
    params = {'public_key': public_key, 'path': path}
    download_link_response = requests.get(YANDEX_DISK_API_URL + '/download', params=params)
    if download_link_response.status_code == 200:
        download_link = download_link_response.json()['href']
        file_response = requests.get(download_link)
        return file_response
    return None


@app.route('/', methods=['GET', 'POST'])
def index():
    files = []
    public_key = ""
    selected_file_type = 'all'
    if request.method == 'POST':
        public_key = request.form['public_key']
        selected_file_type = request.form.get('file_type', 'all')
        files = get_files_from_yandex_disk(public_key, selected_file_type)
    return render_template('index.html', files=files, public_key=public_key, file_types=FILE_TYPES, selected_file_type=selected_file_type)


@app.route('/download', methods=['GET'])
def download():
    public_key = request.args.get('public_key')
    path = request.args.get('path')
    file_response = download_file_from_yandex_disk(public_key, path)
    if file_response:
        return send_file(BytesIO(file_response.content), download_name=path.split('/')[-1], as_attachment=True)
    return redirect(url_for('index'))


@app.route('/download_multiple', methods=['POST'])
def download_multiple():
    public_key = request.form.get('public_key')
    paths = request.form.getlist('paths')

    from zipfile import ZipFile
    from io import BytesIO

    zip_buffer = BytesIO()

    with ZipFile(zip_buffer, 'w') as zip_file:
        for path in paths:
            file_response = download_file_from_yandex_disk(public_key, path)
            if file_response:
                zip_file.writestr(path.split('/')[-1], file_response.content)

    zip_buffer.seek(0)

    return send_file(zip_buffer, download_name="files.zip", as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
