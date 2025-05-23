from flask import Flask, request, render_template, jsonify
import sqlite3
import os
from datetime import datetime
import csv

app = Flask(__name__)

# ---------- Original Query Logic ----------
def query_database(field, value):
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM records WHERE {field} = ?"
    cursor.execute(query, (value,))
    results = cursor.fetchall()
    conn.close()
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    headers = []
    query_made = False

    if request.method == 'POST':
        query_made = True
        criteria = request.form['criteria']
        value = request.form['value']

        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM records WHERE [{criteria}] = ?", (value,))
        results = cursor.fetchall()
        headers = [description[0] for description in cursor.description]
        conn.close()

    return render_template('index.html', results=results, headers=headers, query_made=query_made)

# ---------- New Upload Endpoint ----------
UPLOAD_FOLDER = 'uploaded_comments'
LOG_FILE = 'comments_log.csv'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Make sure CSV has a header
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['value', 'field', 'comment', 'timestamp', 'file_upload_timestamp'])

@app.route('/upload_comments', methods=['POST'])
def upload_comments():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save file with timestamped filename
    upload_time = datetime.now()
    timestamp_str = upload_time.strftime("%Y-%m-%d_%H-%M-%S")
    saved_filename = f"comments_{timestamp_str}.txt"
    saved_path = os.path.join(UPLOAD_FOLDER, saved_filename)
    file.save(saved_path)

    # Parse and log contents
    with open(saved_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    for line in lines:
        parts = line.strip().split('|')
        if len(parts) == 4:
            value, field, comment, timestamp = parts
            entries.append([value, field, comment, timestamp, upload_time.strftime("%Y-%m-%d %H:%M:%S")])

    # Append parsed entries to CSV
    if entries:
        with open(LOG_FILE, 'a', newline='', encoding='utf-8') as log_file:
            writer = csv.writer(log_file)
            writer.writerows(entries)

    return jsonify({'status': 'success', 'entries_added': len(entries)}), 200

# ---------- Run App ----------
if __name__ == '__main__':
    app.run(debug=True)
