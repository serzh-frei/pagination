document.getElementById('sel-img').addEventListener('click', function() {
    // Создаем элемент input для выбора файла
    let input = document.createElement('input');
    input.type = 'file';
    input.accept = '.png, .jpg, .jpeg, .webp, .ico, .svg';

    input.onchange = function(event) {
        // Получаем выбранный файл
        let file = event.target.files[0];
        if (file) {
            // Проверяем размер файла и тип
            let fileSize = file.size;
            let fileExtension = file.name.split('.').pop().toLowerCase();

            // Создаем URL для отображения картинки
            let reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('image').src = e.target.result;
            };
            reader.readAsDataURL(file);

            // Обновляем информацию о файле
            document.getElementById('img-size-info').textContent = (fileSize / 1024).toFixed(2) + ' KB';
            document.getElementById('img-extension-info').textContent = fileExtension;
        }
    };

    // Инициируем клик по input
    input.click();
});

document.getElementById('send-file').addEventListener('click', async function() {
    const imageElementSrc = document.getElementById('image').src;
    const imgTitle = document.getElementById('img-title').value;
    const imgDescription = document.getElementById('img-discription').value;
    const imgTags = document.getElementById('img-tags').value;
    const imgExtension = document.getElementById('img-extension-info').textContent;
    const imgSize = document.getElementById('img-size-info').textContent;

    if (imageElementSrc.indexOf('/img/empty.png') !== -1) {
        alert("Пожалуйста, выберите изображение.");
        return;
    }

    try {
        // Получаем данные изображения в формате Base64
        const base64 = imageElementSrc;

        // Создаем JSON объект с информацией об изображении
        const jsonData = {
            extension: imgExtension,
            size: imgSize,
            description: imgDescription,
            title: imgTitle,
            tags: imgTags,
            base64: base64
        };

        // Преобразуем JSON в строку
        const jsonString = JSON.stringify(jsonData);

        // Определяем размер чанков (например, 1024 символов)
        const chunkSize = 1024;

        // Разбиваем строку JSON на чанки
        const chunks = chunkString(jsonString, chunkSize);

        // Отправляем чанки на сервер
        await sendChunks(chunks);

    } catch (error) {
        if(error.status){
            document.getElementById('response-status').textContent = error.status;
            document.getElementById('response-message').textContent = error.message;
            return;
        }
        
        // Обрабатываем ошибки
        document.getElementById('response-status').textContent = "Ошибка";
        document.getElementById('response-message').textContent = error.message;
    }
});

function chunkString(str, size) {
    const numChunks = Math.ceil(str.length / size);
    const chunks = new Array(numChunks);
    for (let i = 0, o = 0; i < numChunks; ++i, o += size) {
        chunks[i] = str.substr(o, size);
    }
    return chunks;
}

async function sendChunks(chunks) {
    const totalChunks = chunks.length;
    const chanksCountElement = document.getElementById('chank-count');

    document.getElementById('response-status').textContent = "Ожидание";
    document.getElementById('response-message').textContent = "Ожидание";

    for (let i = 0; i < totalChunks; i++) {
        const chunk = chunks[i];
        const payload = {
            id: i + 1,
            total: totalChunks,
            chunk: chunk
        };

        chanksCountElement.textContent = payload.id + '/' + payload.total;

        const response = await fetch('/image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if(!response.ok){
            const error = new Error(response.statusText);
            error.status = response.status;
            throw error;
        }
 
        document.getElementById('response-status').textContent = response.status;
        document.getElementById('response-message').textContent = response.statusText;
    }
}

