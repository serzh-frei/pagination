import flask as f
import base64
import filetype
import os

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



def check_and_create_image(dic):
    img_string = dic['base64']
    for i in range(len(img_string)):
            if img_string[i] == ',':
                img_string = img_string[i+1:]
                break
    img_bytes = base64.b64decode(img_string)


    if filetype.is_image(img_bytes) == True:
        
        title = dic['title']
        
        for i in range(len(dic['title'])):
            if dic['title'][i] in '\/:*?"<>|':
                title = title.replace(dic['title'][i], '')
        
        if title == '':
            title = 'untitled'

        if os.path.exists('gallery') == False:
            os.mkdir('gallery')

        if os.path.exists('gallery/'+title+'.'+dic['extension']) == False:
            with open('gallery/'+title+'.'+dic['extension'], 'wb') as img_file:
                img_file.write(img_bytes)
                return 'Created', 201
        else:
            i = 1
            while os.path.exists('gallery/'+title+' (%s).'%i+dic['extension']) == True:
                i += 1
            with open('gallery/'+title+' (%s).'%i+dic['extension'], 'wb') as img_file:
                img_file.write(img_bytes)
                return 'Created', 201
    
    else:
        return 'Unsupported Media Type', 415


image_base64 = ''
@app.route('/image', methods=['POST'])
def post_img():
    global image_base64
    data = f.request.get_json()
    image_base64 += data['chunk']

    if data['id'] == 1:
        first_chunk = eval(image_base64 + '"}')
        size = first_chunk['size'][:-3]
        if float(size) > 1024:
            image_base64 = ''
            return 'Request Header Fields Too Large', 431


    if data['id'] == data['total']:
        image_data = eval(image_base64)
        image_base64 = ''
        return check_and_create_image(image_data)
    
    return 'accepted', 202



if __name__ == '__main__':
    app.run(debug=True, port=PORT, host=HOST)