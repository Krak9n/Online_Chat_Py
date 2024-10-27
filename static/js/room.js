var socketio = io();  
  const messages = document.getElementById("messages");

  const createMessage = (name, msg, timestamp, ending=null) => {
    let content;
    
    if (msg.data) {
        const fileName = msg.name;
        const fileData = msg.data;

        if (/\.(jpg|jpeg|png|gif)$/i.test(fileName)) {
            // Изображение
            content = `
              <div class="text">
                <span><strong>${name}</strong>:</span>
                <img src="${fileData}" alt="image" style="max-width: 200px;">
                <span class="muted" style="margin-left: 10px;">${timestamp}</span>
              </div>
            `;
        } else if (/\.(mp4|webm|ogg)$/i.test(fileName)) {
            // Видео
            content = `
              <div class="text">
                <span><strong>${name}</strong>:</span>
                <video src="${fileData}" controls style="max-width: 200px;"></video>
                <span class="muted" style="margin-left: 10px;">${timestamp}</span>
              </div>
            `;
        } else if (/\.(mp3|wav|ogg|webm|weba)$/i.test(fileName) || ending==="audio") {
            // Аудио
            content = `
              <div class="text">
                <span><strong>${name}</strong>:</span>
                <audio src="${fileData}" controls></audio>
                <span class="muted" style="margin-left: 10px;">${timestamp}</span>
              </div>
            `;
        } else {
            // Ссылка на файл для скачивания
            content = `
              <div class="text">
                <span><strong>${name}</strong>: <a href="${fileData}" download="${fileName}">${fileName}</a></span>
                <span class="muted" style="margin-left: 10px;">${timestamp}</span>
              </div>
            `;
        }
    } else {
        // Обычное текстовое сообщение
        content = `
          <div class="text">
            <span><strong>${name}</strong>: ${msg}</span>
            <span class="muted" style="margin-left: 10px;">${timestamp}</span>
          </div>
        `;
    }

    messages.innerHTML += content;
};

  // Обработка сообщений от сервера
  socketio.on('message', (data) => {
    if(data.data){
      const username = "{{ session['chatname'] }}";
      if(data.ending){
        createMessage(username, data, data.timestamp, data.ending);
        return
      }
    createMessage(username, data, data.timestamp);
    }else{
      createMessage(data.name, data.message, data.timestamp);
    }
  });

  // Отправка текстового сообщения
  const sendMessage = () => {
    const messageInput = document.getElementById("message");
    const message = messageInput.value.trim();
    if (!message) return;

    socketio.emit("message", { data: message });
    messageInput.value = "";  // Очищаем поле ввода
  };

  // Отправка файла
  const sendFile = () => {
    const fileInput = document.getElementById("file-input");
    const file = fileInput.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const fileData = event.target.result;
      socketio.emit('file', { name: file.name, data: fileData });
    };
    reader.readAsDataURL(file);
  };

  // Работа с аудио
  const startButton = document.getElementById("startButton");
  const stopButton = document.getElementById("stopButton");
  let mediaRecorder;
  let audioChunks = [];
  let stream = null;

  const initStream = async () => {
    if (!stream) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }
    return stream;
  };

  startButton.onclick = async () => {
    audioChunks = [];
    try {
        await initStream();
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const reader = new FileReader();

            reader.onload = () => {
                // Отправка аудиофайла на сервер
                socketio.emit("audioSMS", { name: "Audio Message", data: reader.result });
            };
            reader.readAsDataURL(audioBlob);
        };

        mediaRecorder.start();
        toggleRecordingButtons(true);
    } catch (error) {
        console.error("Error accessing microphone:", error.message);
    }
};

stopButton.onclick = () => {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    toggleRecordingButtons(false);
};
  function toggleRecordingButtons (isRecording) {
    stopButton.style.display = isRecording ? "block" : "none";
    startButton.style.display = isRecording ? "none" : "block";
    stopButton.style.visibility = isRecording ? "visible" : "hidden";
    startButton.style.visibility = isRecording ? "hidden" : "visible";
  };

  window.onunload = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
    }
  };

  socketio.on("audioSMS", data => {
    createMessage(data.name, data.file, data.timestamp);
  });