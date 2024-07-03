import flask as f
import base64
import filetype
import os
from datetime import datetime

PORT = 3000
HOST = 'localhost'

app = f.Flask(__name__)


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

        if os.path.exists('gallery/'+ title + '.' + dic['extension']) == False:
            with open('gallery/' + title + '.' + dic['extension'], 'wb') as img_file:
                img_file.write(img_bytes)
                status_log(title + '.' + dic['extension'], 201, 'Created')
                return 'Created', 201
        else:
            i = 1
            while os.path.exists('gallery/' + title + ' (%s).' %i + dic['extension']) == True:
                i += 1
            with open('gallery/' + title + ' (%s).' %i + dic['extension'], 'wb') as img_file:
                img_file.write(img_bytes)
                status_log(title + '.' + dic['extension'], 201, 'Created')
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