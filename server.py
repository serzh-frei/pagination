import flask as f
import filetype
import os
import psycopg2

import base64
from datetime import datetime


PORT = 3000
HOST = 'localhost'

DATABASE_NAME = 'postgres'
DATABASE_USER = 'postgres'
DATABASE_PASSWORD = '123'
DATABASE_HOST = 'localhost'
DATABASE_PORT = '3001'

app = f.Flask(__name__)

sql_connection = psycopg2.connect(database=DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT)
with sql_connection.cursor() as cursor:
    cursor.execute('''CREATE TABLE IF NOT EXISTS downloads_table (
                   ID integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                   TITLE varchar,
                   TAGS varchar,
                   DESCRIPTION varchar,
                   PATH varchar)''')
    sql_connection.commit()



@app.route('/')
def send_page():
    return f.render_template('index.html')
 

@app.route('/style/main.css')
def send_css():
    return f.send_file('templates/style/main.css'), 200


@app.route('/scripts/main.js')
def send_script():
    return f.send_file('templates/scripts/main.js'), 200


@app.route('/img/empty.png')
def send_img():
     return f.send_file('templates/img/empty.png'), 200



def check_and_create_image(dic: dict):

    img_string = dic['base64']
    for i in range(len(img_string)):
            if img_string[i] == ',':
                img_string = img_string[i+1:]
                break
    img_bytes = base64.b64decode(img_string)

    title = set_name_of_image(dic['title'])

    if filetype.is_image(img_bytes) == True:
        
        if os.path.exists('gallery') == False:
            os.mkdir('gallery')

        path = 'gallery/'+ title + '.' + dic['extension']

        if os.path.exists(path) == False:
            with open(path, 'wb') as img_file:
                img_file.write(img_bytes)
                status_log(title + '.' + dic['extension'], 201, 'Created')
                add_sql_record(title, dic['tags'], dic['description'], path)
                return 'Created', 201
        else:
            i = 1
            numbered_path = 'gallery/' + title + ' (%s).' %i + dic['extension']
            while os.path.exists(numbered_path) == True:
                i += 1
                numbered_path = 'gallery/' + title + ' (%s).' %i + dic['extension']
            with open(numbered_path, 'wb') as img_file:
                img_file.write(img_bytes)
                status_log(title + '.' + dic['extension'], 201, 'Created')
                add_sql_record(title, dic['tags'], dic['description'], numbered_path)
                return 'Created', 201
    
    else:
        status_log(title + '.' + dic['extension'], 415, 'Unsupported Media Type')
        return 'Unsupported Media Type', 415


def status_log(filename, status, message):
    with open('logs.txt', 'a') as file:
        file.write(str(datetime.now()) + ' Имя файла: ' + filename + ' Статус сервера: ' + str(status) +' ' + message + '\n')


def set_name_of_image(title):
    name = title
    
    for i in range(len(title)):
        if title[i] in '\:*?"<>|/':
            name = name.replace(title[i], '')
        
    if name == '':
        name = 'untitled'
    
    return name

def add_sql_record(title, tags, description, path):
    global sql_connection
    with sql_connection.cursor() as cursor:
        cursor.execute(f'''INSERT INTO downloads_table (title, tags, description, path)
                        VALUES ('{title}', '{tags}', '{description}', '{path}')
                        ''')
        sql_connection.commit()



image_base64 = ''
@app.route('/image', methods=['POST'])
def post_img():
    global image_base64
    data = f.request.get_json()
    image_base64 += data['chunk']

    if data['id'] == 1:
        first_chunk = eval(image_base64 + '"}')
        first_chunk['title'] = set_name_of_image(first_chunk['title'])

        size = first_chunk['size'][:-3]
        if float(size) > 1024:
            image_base64 = ''
            status_log(first_chunk['title'] + '.' + first_chunk['extension'], 431, 'Request Header Fields Too Large')
            return 'Request Header Fields Too Large', 431


    if data['id'] == data['total']:
        image_data = eval(image_base64)
        image_base64 = ''
        return check_and_create_image(image_data)
    
    return 'Accepted', 202



if __name__ == '__main__':
    app.run(debug=True, port=PORT, host=HOST)