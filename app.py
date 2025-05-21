from flask import Flask, request, render_template
import sqlite3

app = Flask(__name__)

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
if __name__ == '__main__':
    app.run(debug=True)