from flask import Flask, request, jsonify
import os
import json

app = Flask(__name__)
UPLOAD_FOLDER = 'uploaded_comments'  # make sure this folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload_comments', methods=['POST'])
def upload_comments():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    # Save uploaded file
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # OPTIONAL: Parse and print contents for now
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                print(data)  # you can store this into a database, CSV, etc.
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'success', 'message': 'File uploaded and processed successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)
