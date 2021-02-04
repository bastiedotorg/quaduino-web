class Application {
    ws = null;

    init() {
        this.ws = new WebSocket('ws://' + location.host + '/ws');
        this.ws.binaryType = 'arraybuffer';

        this.ws.onopen = function () {
            console.log('Connected.')
        };
        this.ws.onmessage = function (evt) {
            let message = JSON.parse(evt.data);
            document.getElementById("text-output").innerHTML += message.message + "\r\n";
            console.log(message);
        };
        this.ws.onclose = function () {
            console.log('Connection is closed...');
        };
    }
}

let app = new Application();
app.init();
