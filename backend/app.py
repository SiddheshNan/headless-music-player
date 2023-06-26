import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import json
import logging
from pygame import mixer
from flask_cors import CORS
from flask import Flask, jsonify, request, send_from_directory, render_template



logging.basicConfig(format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d | %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S', level=logging.INFO)

app = Flask(__name__)
CORS(app)
mixer.init()

static_path = os.path.join(os.path.dirname(__file__), 'static')

MUSIC = []

STATE = {
    'isPaused': True,
    'fileName': "",
    'volume': 0.5
}

CONFIG_FILE_NAME = "config/config.json"


def read_music_folder():
    global MUSIC
    logging.debug(f"Reading Music Folder")
    MUSIC = []
    files = os.listdir('./music')
    for file in files:
        if os.path.splitext(file)[1] == ".mp3":
            MUSIC.append(file)

def save_state():
    logging.debug("Saving State")
    config_file_content = {
        'isPaused': STATE['isPaused'],
        'fileName': STATE['fileName'],
        'volume': STATE['volume']
    }
    json.dump(config_file_content, open(CONFIG_FILE_NAME, 'w'))

def on_start():
    logging.info("on_start")
    config_file_content = json.load(open(CONFIG_FILE_NAME))

    STATE['volume'] = config_file_content['volume']
    mixer.music.set_volume(STATE['volume'])

    STATE['isPaused'] = config_file_content['isPaused']
    STATE['fileName'] = config_file_content['fileName']

    if STATE['fileName'] != "":
        full_path = os.path.join(os.getcwd(), "music", STATE['fileName'])

        if not os.path.isfile(full_path):
            logging.error("on_start: File not found")
            STATE['fileName'] = ""
            STATE['isPaused'] = True
            save_state()
            return
        
        mixer.music.load(full_path)
        mixer.music.play(-1)

        if STATE['isPaused']:
            logging.info("on_start: Pausing")
            mixer.music.pause()





@app.route('/')
@app.route('/index.html')
def index_html():
    return render_template("index.html")


@app.route('/state')
def get_state():
    return jsonify(STATE)


@app.route('/state', methods=["POST"])
def set_state():
    global STATE, MUSIC
    body = request.get_json()

    if "pause" in body:
        if STATE['fileName'] == "":
            return jsonify({'err': 'Please start the music first!'}), 400
        elif STATE['isPaused']:
            return jsonify({'err': 'The music is already paused!'}), 400
        STATE['isPaused'] = True
        mixer.music.pause()
        save_state()
        return jsonify({'msg': 'ok'})

    if "resume" in body:
        if STATE['fileName'] == "":
            return jsonify({'err': 'Please start the music first!'}), 400
        elif not STATE['isPaused']:
            return jsonify({'err': 'The music is already playing!'}), 400
        STATE['isPaused'] = False
        mixer.music.unpause()
        save_state()
        return jsonify({'msg': 'ok'})

    if "stop" in body:
        STATE['fileName'] = ""
        STATE['isPaused'] = True
        mixer.music.stop()
        save_state()
        return jsonify({'msg': 'ok'})

    if "play" in body:
        fileName = body['play']
        if fileName not in MUSIC:
            return jsonify({'err': 'The specified file not found'}), 400

        STATE['isPaused'] = False
        STATE['fileName'] = fileName

        full_path = os.path.join(os.getcwd(), "music", fileName)

        mixer.music.load(full_path)
        mixer.music.play(-1)

        save_state()

        return jsonify({'msg': 'ok'})

    if "volume" in body:
        volume = body['volume']
        mixer.music.set_volume(volume)
        STATE['volume'] = volume
        save_state()
        return jsonify({'msg': 'ok'})

    return jsonify({'err': 'Please choose specified operation'}), 400


@app.route('/music_list')
def get_music_list():
    return jsonify(MUSIC)


@app.route('/reload_music_list')
def reload_music():
    read_music_folder()
    return jsonify(MUSIC)


@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('assets', path)

# @app.route('/<path:path>')
# def serve_static(path):
#     if os.path.isdir(os.path.join(static_path, path)):
#         path = os.path.join(path, 'index.html')
#     return send_from_directory(static_path, path)


if __name__ == '__main__':
    logging.info("App Started")
    read_music_folder()
    on_start()
    app.run(host='0.0.0.0', port=8000)
