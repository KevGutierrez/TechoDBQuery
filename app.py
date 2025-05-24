from flask import Flask, request, render_template, jsonify, send_from_directory
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

# ---------- Static file serving for database ----------
@app.route('/static/data.db')
def serve_database():
    return app.send_static_file('data.db')

# ---------- Upload Endpoint for 5-part format ----------
UPLOAD_FOLDER = 'uploaded_comments'
LOG_FILE = 'comments_log.csv'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Make sure CSV has updated header for 5-part format
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['cedula', 'nombre', 'comunidad', 'comment', 'timestamp', 'file_upload_timestamp'])

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
    
    # Parse and log contents with 5-part format
    with open(saved_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    entries = []
    for line in lines:
        parts = line.strip().split('|')
        if len(parts) == 5:  # Updated to expect 5 parts
            cedula, nombre, comunidad, comment, timestamp = parts
            entries.append([cedula, nombre, comunidad, comment, timestamp, upload_time.strftime("%Y-%m-%d %H:%M:%S")])
        else:
            print(f"Warning: Line has {len(parts)} parts instead of 5: {line.strip()}")
    
    # Append parsed entries to CSV
    if entries:
        with open(LOG_FILE, 'a', newline='', encoding='utf-8') as log_file:
            writer = csv.writer(log_file)
            writer.writerows(entries)
    
    return jsonify({'status': 'success', 'entries_added': len(entries)}), 200

# ---------- NEW: Admin Routes for Viewing Comments ----------

@app.route('/admin/comments')
def list_comments():
    """List all uploaded comment files and show summary"""
    # Get all .txt files
    txt_files = []
    if os.path.exists(UPLOAD_FOLDER):
        all_files = os.listdir(UPLOAD_FOLDER)
        txt_files = [f for f in all_files if f.endswith('.txt')]
        txt_files.sort(reverse=True)  # Show newest first
    
    # Count total comments from CSV
    total_comments = 0
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                total_comments = sum(1 for row in reader) - 1  # Subtract header row
        except:
            total_comments = 0
    
    # Create HTML response
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Comentarios - Panel Admin</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .file-list {{ margin: 20px 0; }}
            .file-item {{ 
                background-color: #f9f9f9; 
                padding: 10px; 
                margin: 5px 0; 
                border-left: 4px solid #007bff; 
                border-radius: 3px; 
            }}
            .file-item a {{ text-decoration: none; color: #007bff; font-weight: bold; }}
            .file-item a:hover {{ text-decoration: underline; }}
            .csv-section {{ 
                background-color: #e8f5e8; 
                padding: 15px; 
                border-radius: 5px; 
                margin-top: 30px; 
            }}
            .btn {{ 
                background-color: #28a745; 
                color: white; 
                padding: 8px 16px; 
                text-decoration: none; 
                border-radius: 3px; 
                display: inline-block; 
                margin: 5px; 
            }}
            .btn:hover {{ background-color: #218838; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📝 Panel de Comentarios</h1>
            <p><strong>Total de comentarios registrados:</strong> {total_comments}</p>
            <p><strong>Archivos de texto subidos:</strong> {len(txt_files)}</p>
        </div>
        
        <h2>📄 Archivos de Comentarios (.txt)</h2>
    """
    
    if txt_files:
        html += '<div class="file-list">'
        for file in txt_files:
            file_path = os.path.join(UPLOAD_FOLDER, file)
            try:
                # Get file modification time
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                mod_time_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Get file size
                file_size = os.path.getsize(file_path)
                
                html += f'''
                <div class="file-item">
                    <a href="/admin/comments/{file}">{file}</a>
                    <br><small>📅 {mod_time_str} | 📊 {file_size} bytes</small>
                </div>
                '''
            except:
                html += f'<div class="file-item"><a href="/admin/comments/{file}">{file}</a></div>'
        html += '</div>'
    else:
        html += '<p><em>No se han subido archivos de comentarios aún.</em></p>'
    
    # CSV section
    html += f'''
        <div class="csv-section">
            <h3>📊 Registro Consolidado (CSV)</h3>
            <p>Todos los comentarios también se guardan en un archivo CSV consolidado:</p>
            <a href="/admin/csv" class="btn">📋 Ver comments_log.csv</a>
            <a href="/admin/csv/download" class="btn">⬇️ Descargar CSV</a>
        </div>
        
        <hr style="margin: 30px 0;">
        <p><small>🏠 <a href="/">Volver al inicio</a></small></p>
    </body>
    </html>
    '''
    
    return html

@app.route('/admin/comments/<filename>')
def view_comment_file(filename):
    """View individual comment file with nice formatting"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            return f"<h2>❌ Archivo no encontrado: {filename}</h2>", 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Parse the content
        lines = content.split('\n')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Comentario - {filename}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .comment-item {{ 
                    background-color: #f9f9f9; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-left: 4px solid #007bff; 
                    border-radius: 3px; 
                }}
                .field {{ margin: 5px 0; }}
                .field strong {{ color: #333; }}
                .comment-text {{ 
                    background-color: #fff; 
                    padding: 10px; 
                    margin: 10px 0; 
                    border-radius: 3px; 
                    border: 1px solid #ddd; 
                }}
                .back-btn {{ 
                    background-color: #6c757d; 
                    color: white; 
                    padding: 8px 16px; 
                    text-decoration: none; 
                    border-radius: 3px; 
                    display: inline-block; 
                }}
                .back-btn:hover {{ background-color: #5a6268; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>💬 Archivo de Comentario</h1>
                <h2>{filename}</h2>
            </div>
        """
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                parts = line.split('|')
                if len(parts) == 5:
                    cedula, nombre, comunidad, comment, timestamp = parts
                    html += f'''
                    <div class="comment-item">
                        <h3>💬 Comentario #{i}</h3>
                        <div class="field"><strong>👤 Cédula:</strong> {cedula}</div>
                        <div class="field"><strong>🏷️ Nombre:</strong> {nombre}</div>
                        <div class="field"><strong>🏘️ Comunidad:</strong> {comunidad}</div>
                        <div class="field"><strong>📅 Fecha:</strong> {timestamp}</div>
                        <div class="comment-text">
                            <strong>💭 Comentario:</strong><br>
                            {comment}
                        </div>
                    </div>
                    '''
                else:
                    html += f'<div class="comment-item"><strong>Línea {i}:</strong> {line}</div>'
        
        html += '''
            <br>
            <a href="/admin/comments" class="back-btn">← Volver a la lista</a>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f"<h2>❌ Error al leer el archivo:</h2><p>{str(e)}</p>", 500

@app.route('/admin/csv')
def view_csv_log():
    """View the CSV log file with nice formatting"""
    if not os.path.exists(LOG_FILE):
        return "<h2>❌ El archivo CSV no existe aún</h2>", 404
    
    try:
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Registro CSV de Comentarios</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; font-weight: bold; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .back-btn { 
                    background-color: #6c757d; 
                    color: white; 
                    padding: 8px 16px; 
                    text-decoration: none; 
                    border-radius: 3px; 
                    display: inline-block; 
                    margin: 10px 0;
                }
                .back-btn:hover { background-color: #5a6268; }
                .header { background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Registro Consolidado de Comentarios (CSV)</h1>
            </div>
        """
        
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if rows:
            html += '<table>'
            # Header
            html += '<tr>'
            for header in rows[0]:
                html += f'<th>{header}</th>'
            html += '</tr>'
            
            # Data rows
            for row in rows[1:]:
                html += '<tr>'
                for cell in row:
                    html += f'<td>{cell}</td>'
                html += '</tr>'
            html += '</table>'
        else:
            html += '<p>El archivo CSV está vacío.</p>'
        
        html += '''
            <a href="/admin/comments" class="back-btn">← Volver a comentarios</a>
            <a href="/admin/csv/download" class="back-btn">⬇️ Descargar CSV</a>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f"<h2>❌ Error al leer el CSV:</h2><p>{str(e)}</p>", 500

@app.route('/admin/csv/download')
def download_csv():
    """Download the CSV file"""
    if os.path.exists(LOG_FILE):
        return send_from_directory('.', LOG_FILE, as_attachment=True)
    else:
        return "❌ Archivo CSV no encontrado", 404

# ---------- Run App ----------
if __name__ == '__main__':
    app.run(debug=True)