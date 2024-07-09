import flask as f
import filetype
import psycopg2

import base64
import os
import subprocess
from datetime import datetime



# переменные окружения
PORT = 3000
HOST = '0.0.0.0'

# DATABASE_NAME = 'postgres'
# DATABASE_USER = 'postgres'
# DATABASE_PASSWORD = '123'
# DATABASE_HOST = 'localhost'
# DATABASE_PORT = '3001'

DATABASE_NAME = os.getenv('DATABASE_NAME')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_PORT = os.getenv('DATABASE_PORT')


# создание сервера
app = f.Flask(__name__)
# корень директории для сохранения файлов
root_dir = os.path.dirname(os.path.abspath(__file__)) + '/'




# GET-запрос к корневому роуту отправляет страницу index.html
@app.route('/')
def send_page():
    return f.render_template('index.html')
 

# последующие GET-запросы отправляют соответствующие файлы, требуемые для работы страницы
@app.route('/style/main.css')
def send_css():
    return f.send_file('templates/style/main.css'), 200


@app.route('/scripts/main.js')
def send_script():
    return f.send_file('templates/scripts/main.js'), 200


@app.route('/img/empty.png')
def send_img():
     return f.send_file('templates/img/empty.png'), 200




# класс реализации работы с PostgreSQL и базами данных

class SQL_Manager:


    # создание базы данных (при её отсутствии) и её бэкапа 
    def create_bd_and_backup():

        # подключаемся к системной базе данных
        sql_connection = psycopg2.connect(database = DATABASE_NAME, user = DATABASE_USER, password = DATABASE_PASSWORD, host = DATABASE_HOST, port = DATABASE_PORT)
        # свойство autocommit позволяет автоматически отправлять sql-инструкции 
        sql_connection.autocommit = True

        # объект cursor позволяет выполнять инструкции sql
        with sql_connection.cursor() as cursor:

            # т.к. postgress не поддерживает проверку существования баз, пытаемся получить информацию от неё
            cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'pagination_db'")
            exists = cursor.fetchone()

            # и, если информации нет, создаём базу
            if not exists:

                # создаём базу pagination_db
                cursor.execute('CREATE DATABASE pagination_db')
                sql_connection.commit()

                # если директории backups для бэкапов не существует, создаём
                if os.path.exists(root_dir + 'backups') == False:
                    os.mkdir(root_dir + 'backups')
                
                # через консоль запускаем утилиту pg_dump, создающую бэкапы для баз
                # print("Введите пароль от учетной записи PostgreSQL ниже. Вводимая информация не выводится на экран. По окончании ввода нажмите Enter.")
            command = [
        'podman', 'exec', '-it', 'postgres', 'pg_dump',
        '-d', 'pagination_db', '-h', DATABASE_HOST, '-p', DATABASE_PORT,
        '-U', DATABASE_USER, '-f', root_dir + 'backups/backup.sql', '--schema-only'
    ]
            p = subprocess.Popen(command)
            p.communicate()

        # закрываем соединение с системной базой
        sql_connection.close()

    
    # функция создаёт в новой базе данных таблицу (если она существует)
    def create_table():

        # открываем новое соединение с нашей новой базой
        sql_connection = psycopg2.connect(database='pagination_db', user=DATABASE_USER, password=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT)
        sql_connection.autocommit = True
        
        # объект cursor позволяет выполнять инструкции sql
        with sql_connection.cursor() as cursor:

            # создаём таблицу с полями айди, названия, тегов, описания и пути к картинке
            # каждое поле кроме айди является строковым типом данных 
            # инструкция IF NOT EXISTS создаст таблицу только при её отсутствии
            cursor.execute('''CREATE TABLE IF NOT EXISTS downloads_table (
                        ID integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        TITLE varchar,
                        TAGS varchar,
                        DESCRIPTION varchar,
                        PATH varchar)''')
        
        # закрываем соединение с базой
        sql_connection.close()


    # функция записывает в таблицу поля названия, теги, описание и относительный путь к картинке
    def add_sql_record(title: str, tags: str, description: str, path: str):

        # открываем соединение с базой
        sql_connection = psycopg2.connect(database='pagination_db', user=DATABASE_USER, password=DATABASE_PASSWORD, host=DATABASE_HOST, port=DATABASE_PORT)
        sql_connection.autocommit = True

        # вставляем данные в таблицу
        with sql_connection.cursor() as cursor:
            cursor.execute(f'''INSERT INTO downloads_table (title, tags, description, path)
                            VALUES ('{title}', '{tags}', '{description}', '{path}')
                            ''')

        # закрываем соединение с базой
        sql_connection.close()




# класс реализации обработки пагинированных запросов

class Pagination_Manager:

    # строка, в которую суммируются чанки при приёме запросов
    dict_base64 = ''


    # функция проверки полученного файла на изображение и сохранения его в галерее. 
    # передаётся полученный словарь данных
    def check_and_create_image(self, dic: dict):

        # вычищаем поле, содержащее картинку в формате base64 от лишней информации, не входящей в строку
        # информация находится в начале строки и выглядит как: data:image/png;base64,
        # эта информация всегда заканчивается запятой

        # достаём неочищенную строку
        img_base64 = dic['base64']

        # проходимся циклом по всем символам строки при помощи индексов
        for i in range(len(img_base64)):
                
                # если находим символ запятой, делаем срез строки от этой запятой до конца и выходим из цикла
                if img_base64[i] == ',':
                    img_base64 = img_base64[i+1:]
                    break
        
        # полученную base64 строку декодируем в байты и сохраняем в переменной
        img_bytes = base64.b64decode(img_base64)
        

        # производим над полем названия проверку на запрещенные символы или отсутствие названия
        title = self.set_name_of_image(dic['title'])



        # если картинка действительно является картинкой, а не каким-либо другим форматом
        if filetype.is_image(img_bytes) == True:
            
            # создаём директорию галереи, если она не создана
            if os.path.exists(root_dir + 'gallery') == False:
                os.mkdir(root_dir + 'gallery')
            
            # относительный путь до будущего файла
            path = 'gallery/'+ title + '.' + dic['extension']


            # блок проверки, не существует ли в директории файла с таким же именем
            if os.path.exists(root_dir + path) == False:
                
                # если не существует, то создаём, записываем в журнал, базу данных и возвращаем соответствующий статус
                with open(root_dir + path, 'wb') as img_file:
                    img_file.write(img_bytes)
                    self.status_log(title + '.' + dic['extension'], 201, 'Created')
                    SQL_Manager.add_sql_record(title, dic['tags'], dic['description'], path)
                    return 'Created', 201
            
            # если же имя существует, мы сгенерируем файл с цифровой припиской к названию, по типу "untitled (1).png"
            else:
                # счётчик для припички
                i = 1
                # относительный путь будущего файла с цифровой припиской
                numbered_path = 'gallery/' + title + ' (%s).' %i + dic['extension']
                
                # циклом проверяем, существует ли название с такой цифровой припиской
                # пока такое название существует, каждый раз прибавляем к цифре единицу и проверяем заново
                while os.path.exists(root_dir + numbered_path) == True:
                    i += 1
                    numbered_path = 'gallery/' + title + ' (%s).' %i + dic['extension']

                # когда же мы нашли название, которого не существует, мы создаём файл с таким названием, все записываем и возвращаем статус
                with open(root_dir + numbered_path, 'wb') as img_file:
                    img_file.write(img_bytes)
                    self.status_log(title + '.' + dic['extension'], 201, 'Created')
                    SQL_Manager.add_sql_record(title, dic['tags'], dic['description'], numbered_path)
                    return 'Created', 201
        

        # если картинка не картинка, заносим в журнал и возвращаем соотвествующий статус 
        else:
            self.status_log(title + '.' + dic['extension'], 415, 'Unsupported Media Type')
            return 'Unsupported Media Type', 415
    


    # функция логгирования, записывающая события в журнал событий logs.txt
    # принимает имя файла, статус события и сообщение о событии
    def status_log(self, filename: str, status: str, message: str):

        if os.path.exists(root_dir + 'logs') == False:
            os.mkdir('logs')
        with open(root_dir + 'logs/logs.txt', 'a') as file:

            file.write(str(datetime.now()) + ' Имя файла: ' + filename + ' Статус сервера: ' + str(status) +' ' + message + '\n')



    # функция проверки имени файла на запрещённые символы и пустое имя
    # принимает строку имени
    # возвращает изменённую строку
    def set_name_of_image(self, title: str):
        
        # копия имени
        name = title
        
        # проходимся по имени
        for i in range(len(title)):
            # каждый запрещённый символ удаляем
            if title[i] in ':*?"<>|/':
                name = name.replace(title[i], '')
        
        # если имя не задано, ему присваивается имя untitled
        if name == '':
            name = 'untitled'
        
        return name


# создаём экземпляр класса, к которому будем обращаться при приёме запроса
pag = Pagination_Manager()


# POST-запрос к роуту /image
@app.route('/image', methods=['POST'])
def post_img():

    # даём возможность использовать ранее созданный экземпляр
    global pag

    # с запросом получаем json с чанком и его номером
    data = f.request.get_json()
    # чанк приплюсовываем к остальным
    pag.dict_base64 += data['chunk']


    # на этапе приёма самого первого чанка проводим проверку на размер файла
    if data['id'] == 1:

        # конвертируем чанк в словарь
        first_chunk = eval(pag.dict_base64 + '"}')
        # проверяем имя файла, чтобы использовать его в дальнейшем в логах
        first_chunk['title'] = pag.set_name_of_image(first_chunk['title'])

        # отлавливаем из словаря размер и вырезаем из него приписку " KB"
        size = first_chunk['size'][:-3]
        
        # если размер файла больше 1024 кб (или 1 мб), прерываем передачу, фиксируем в логах и отправляем соответствующий статус
        if float(size) > 1024:

            # обнуляем чанки для следующей передачи
            pag.dict_base64 = ''

            pag.status_log(first_chunk['title'] + '.' + first_chunk['extension'], 431, 'Request Header Fields Too Large')
            return 'Request Header Fields Too Large', 431


    # если чанк является последним, собираем картинку и проводим необходимые для создания файла процедуры
    if data['id'] == data['total']:
        # конвертируем строку чанков в словарь
        image_data = eval(pag.dict_base64)
        # обнуляем чанки для следующей передачи
        pag.dict_base64 = ''
        # производим проверку и создание картинки
        return pag.check_and_create_image(image_data)
    
    # пока чанки отправляются на сервер, возвращаем статус Accepted, говорящий о том, что передача продолжается
    return 'Accepted', 202





# при запуске скрипта 
if __name__ == '__main__':
    # создаём базу данных и бэкап, если они не созданы
    SQL_Manager.create_bd_and_backup()
    # создаём в базе данных таблицу, если она не создана
    SQL_Manager.create_table()
    # запускаем сервер
    app.run(debug=True, port=PORT, host=HOST)
    