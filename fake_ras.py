import os

from flask import Flask, jsonify, request

__version__ = "0.0.1"

app = Flask(__name__)


@app.route('/upload/<survey>/<ce>/<filename>', methods=['POST'])
def post_file(survey, ce, filename):
    os.makedirs("./upload/{}/{}".format(survey, ce), exist_ok=True)

    with open("./upload/{}/{}/{}".format(survey, ce, filename), "wb") as fp:
        data = request.data
        fp.write(data)

    return jsonify({'status': 'uploaded'})


@app.route('/list', methods=['GET'])
def list_files():
    return jsonify({'name' :'file1'})


if __name__ == '__main__':
    # Startup
    app.logger.info("Starting server: version='{}'".format(__version__))
    port = int(os.getenv("PORT", 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
