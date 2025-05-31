from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, url_for
import sqlite3
import os
from datetime import datetime
import csv
import json
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Configuration
UPLOAD_FOLDER = 'uploaded_comments'
LOG_FILE = 'comments_log.csv'
DATABASE_FILE = 'data.db'
RECENT_SEARCHES_FILE = 'recent_searches.json'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize CSV log file
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['cedula', 'nombre', 'comunidad', 'comment', 'timestamp'])

# Initialize recent searches file
if not os.path.exists(RECENT_SEARCHES_FILE):
    with open(RECENT_SEARCHES_FILE, 'w', encoding='utf-8') as f:
        json.dump({'CEDULA': [], 'CONTACTO 1': [], 'NOMBRE COMPLETO': []}, f)

def normalize_string(text):
    """Normalize string for better search matching (similar to Flutter app)"""
    if not text:
        return ""
    # Convert to lowercase and remove accents
    import unicodedata
    text = str(text).lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text

def get_recent_searches():
    """Get recent searches from file"""
    try:
        with open(RECENT_SEARCHES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'CEDULA': [], 'CONTACTO 1': [], 'NOMBRE COMPLETO': []}

def save_recent_search(field, term):
    """Save a recent search term"""
    if not term.strip():
        return
    
    searches = get_recent_searches()
    if field in searches:
        # Remove if exists and add to beginning
        if term in searches[field]:
            searches[field].remove(term)
        searches[field].insert(0, term)
        
        # Keep only last 5 searches
        searches[field] = searches[field][:5]
        
        with open(RECENT_SEARCHES_FILE, 'w', encoding='utf-8') as f:
            json.dump(searches, f, ensure_ascii=False)

def get_database_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

def query_by_name(name_term):
    """Query database by name with partial matching"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # Use LIKE for partial matching and normalize for better results
    query = """
    SELECT * FROM records 
    WHERE LOWER([NOMBRE COMPLETO]) LIKE ? 
    OR LOWER([NOMBRE COMPLETO]) LIKE ?
    """
    
    name_lower = name_term.lower()
    cursor.execute(query, (f'%{name_lower}%', f'{name_lower}%'))
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def query_database(field, value, filters=None):
    """Query database with optional filters"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # Base query
    if field == "NOMBRE COMPLETO":
        results = query_by_name(value)
    else:
        # Exact match for CEDULA and CONTACTO 1
        field_name = f'[{field}]' if field == "CONTACTO 1" else field
        cursor.execute(f"SELECT * FROM records WHERE {field_name} = ?", (value,))
        results = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # Apply filters
    if filters:
        if filters.get('comunidad') and filters['comunidad'] != 'Todas':
            results = [r for r in results if r.get('COMUNIDAD', '').lower() == filters['comunidad'].lower()]
        
        if filters.get('estado') and filters['estado'] != 'Todos':
            results = [r for r in results if r.get('ESTADO', '').lower() == filters['estado'].lower()]
    
    return results

def get_database_info():
    """Get database information like last sync time"""
    try:
        stat = os.stat(DATABASE_FILE)
        return {
            'last_modified': datetime.fromtimestamp(stat.st_mtime),
            'size': stat.st_size
        }
    except:
        return {'last_modified': None, 'size': 0}

def has_unsynced_comments():
    """Check if there are unsynced comments"""
    return os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > len('cedula,nombre,comunidad,comment,timestamp\n')

def get_unsynced_comments():
    """Get all unsynced comments"""
    comments = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                comments = list(reader)
        except:
            pass
    return comments

def save_comment(record_data, comment_text):
    """Save a comment to the log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Extract key information from record
    cedula = record_data.get('CEDULA', 'N/A')
    nombre = record_data.get('NOMBRE COMPLETO', 'N/A')
    comunidad = record_data.get('COMUNIDAD', 'N/A')
    
    # Append to CSV
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([cedula, nombre, comunidad, comment_text, timestamp])

@app.route('/')
def index():
    """Main search page"""
    db_info = get_database_info()
    has_comments = has_unsynced_comments()
    
    return render_template('index.html', 
                         db_info=db_info,
                         has_unsynced_comments=has_comments,
                         recent_searches=get_recent_searches())

@app.route('/search', methods=['POST'])
def search():
    """Handle search requests"""
    data = request.get_json()
    
    field = data.get('field', 'CEDULA')
    value = data.get('value', '').strip()
    filters = data.get('filters', {})
    
    if not value:
        return jsonify({'error': 'Valor de búsqueda requerido'}), 400
    
    # Save recent search
    save_recent_search(field, value)
    
    # Perform search
    results = query_database(field, value, filters)
    
    return jsonify({
        'results': results,
        'count': len(results),
        'query': {'field': field, 'value': value, 'filters': filters}
    })

@app.route('/add_comment', methods=['POST'])
def add_comment():
    """Add a comment to a record"""
    data = request.get_json()
    
    record_data = data.get('record')
    comment_text = data.get('comment', '').strip()
    
    if not record_data or not comment_text:
        return jsonify({'error': 'Datos incompletos'}), 400
    
    try:
        save_comment(record_data, comment_text)
        return jsonify({'success': True, 'message': 'Comentario añadido correctamente'})
    except Exception as e:
        return jsonify({'error': f'Error al guardar comentario: {str(e)}'}), 500

@app.route('/get_suggestions/<field>')
def get_suggestions(field):
    """Get recent search suggestions for a field"""
    searches = get_recent_searches()
    return jsonify(searches.get(field, []))

@app.route('/comments')
def view_comments():
    """View all unsynced comments"""
    comments = get_unsynced_comments()
    return render_template('comments.html', comments=comments)

@app.route('/comments/delete', methods=['POST'])
def delete_comment():
    """Delete a comment (simulate by marking as deleted)"""
    data = request.get_json()
    comment_id = data.get('id')  # This would be row index in a real implementation
    
    # For simplicity, we'll just return success
    # In a real implementation, you'd need to handle comment deletion properly
    return jsonify({'success': True})

@app.route('/sync_database', methods=['POST'])
def sync_database():
    """Simulate database sync (in real app, this would update from server)"""
    try:
        # In a real implementation, this would:
        # 1. Download latest database from server
        # 2. Upload unsynced comments to server
        # 3. Clear local unsynced comments
        
        # For now, we'll just simulate success
        return jsonify({
            'success': True, 
            'message': 'Base de datos sincronizada correctamente',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': f'Error al sincronizar: {str(e)}'}), 500

# ---------- Admin Routes (keeping your existing functionality) ----------

@app.route('/admin/comments')
def admin_list_comments():
    """Admin page to list all comments"""
    comments = get_unsynced_comments()
    
    # Get file info
    txt_files = []
    if os.path.exists(UPLOAD_FOLDER):
        all_files = os.listdir(UPLOAD_FOLDER)
        txt_files = [f for f in all_files if f.endswith('.txt')]
        txt_files.sort(reverse=True)
    
    return render_template('admin_comments.html', 
                         comments=comments,
                         txt_files=txt_files,
                         total_comments=len(comments))

@app.route('/admin/comments/<filename>')
def admin_view_comment_file(filename):
    """View individual comment file"""
    try:
        file_path = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
        if not os.path.exists(file_path):
            return f"Archivo no encontrado: {filename}", 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        lines = content.split('\n')
        parsed_comments = []
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                parts = line.split('|')
                if len(parts) >= 4:  # Flexible parsing
                    parsed_comments.append({
                        'line_number': i,
                        'cedula': parts[0] if len(parts) > 0 else '',
                        'nombre': parts[1] if len(parts) > 1 else '',
                        'comunidad': parts[2] if len(parts) > 2 else '',
                        'comment': parts[3] if len(parts) > 3 else '',
                        'timestamp': parts[4] if len(parts) > 4 else ''
                    })
        
        return render_template('admin_comment_file.html', 
                             filename=filename,
                             comments=parsed_comments)
        
    except Exception as e:
        return f"Error al leer el archivo: {str(e)}", 500

@app.route('/admin/csv')
def admin_view_csv():
    """View CSV log"""
    comments = get_unsynced_comments()
    return render_template('admin_csv.html', comments=comments)

@app.route('/admin/csv/download')
def admin_download_csv():
    """Download CSV file"""
    if os.path.exists(LOG_FILE):
        return send_from_directory('.', LOG_FILE, as_attachment=True)
    else:
        return "Archivo CSV no encontrado", 404

@app.route('/upload_comments', methods=['POST'])
def upload_comments():
    """Upload comments from mobile app"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
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
            if len(parts) >= 4:  # More flexible parsing
                cedula = parts[0] if len(parts) > 0 else ''
                nombre = parts[1] if len(parts) > 1 else ''
                comunidad = parts[2] if len(parts) > 2 else ''
                comment = parts[3] if len(parts) > 3 else ''
                timestamp = parts[4] if len(parts) > 4 else upload_time.strftime("%Y-%m-%d %H:%M:%S")
                
                entries.append([cedula, nombre, comunidad, comment, timestamp])
        
        # Append to CSV
        if entries:
            with open(LOG_FILE, 'a', newline='', encoding='utf-8') as log_file:
                writer = csv.writer(log_file)
                writer.writerows(entries)
        
        return jsonify({'status': 'success', 'entries_added': len(entries)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/data.db')
def serve_database():
    """Serve database file for offline access"""
    return send_from_directory('.', DATABASE_FILE)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Error interno del servidor"), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)