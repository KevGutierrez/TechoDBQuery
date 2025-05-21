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
    results = []
    headers = []
    if request.method == 'POST':
        criteria = request.form['criteria']  # 'CEDULA' or 'CONTACTO'
        value = request.form['value']

        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()

        query = f"SELECT * FROM records WHERE {criteria} = ?"
        cursor.execute(query, (value,))
        results = cursor.fetchall()

        # Get column names
        headers = [description[0] for description in cursor.description]

        conn.close()
    return render_template('index.html', results=results, headers=headers)
if __name__ == '__main__':
    app.run(debug=True)