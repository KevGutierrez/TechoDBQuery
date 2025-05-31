from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, url_for
import sqlite3
import os
import requests
from datetime import datetime
import csv
import json
import re
from werkzeug.utils import secure_filename
from flask import send_from_directory

# Configuration constants - define these BEFORE app initialization
UPLOAD_FOLDER = 'uploaded_comments'
LOG_FILE = 'comments_log.csv'
DATABASE_FILE = 'data.db'
RECENT_SEARCHES_FILE = 'recent_searches.json'

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.static_folder = 'static'

# Add template filter
@app.template_filter('tojsonfilter')
def tojsonfilter(obj):
    return json.dumps(obj)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

def init_database():
    """Initialize the database and required files"""
    try:
        # Create required directories
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Initialize log file if it doesn't exist
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['cedula', 'nombre', 'comunidad', 'comment', 'timestamp'])
        
        # Initialize recent searches file
        if not os.path.exists(RECENT_SEARCHES_FILE):
            with open(RECENT_SEARCHES_FILE, 'w', encoding='utf-8') as f:
                json.dump({'CEDULA': [], 'CONTACTO 1': [], 'NOMBRE COMPLETO': []}, f)
                
        # Create database if it doesn't exist
        if not os.path.exists(DATABASE_FILE):
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            # Create your tables here if needed
            conn.close()
            
        return True
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False

# Add these new routes and functions
@app.route('/edit_comment', methods=['POST'])
def edit_comment():
    try:
        data = request.get_json()
        comment_id = data.get('commentId')
        new_comment = data.get('newComment')
        
        if not comment_id or not new_comment:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        # Read all comments
        comments = []
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            comments = list(reader)
        
        # Find and update the comment
        found = False
        for comment in comments:
            if comment.get('id') == comment_id:
                comment['comment'] = new_comment
                comment['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                found = True
                break
        
        if not found:
            return jsonify({'error': 'Comentario no encontrado'}), 404
        
        # Write back all comments
        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=comments[0].keys())
            writer.writeheader()
            writer.writerows(comments)
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Edit comment error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    try:
        data = request.get_json()
        comment_id = data.get('commentId')
        
        if not comment_id:
            return jsonify({'error': 'ID de comentario requerido'}), 400
        
        # Read all comments
        comments = []
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            comments = list(reader)
        
        # Filter out the comment to delete
        updated_comments = [c for c in comments if c.get('id') != comment_id]
        
        if len(updated_comments) == len(comments):
            return jsonify({'error': 'Comentario no encontrado'}), 404
        
        # Write back remaining comments
        with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=updated_comments[0].keys() if updated_comments else ['id', 'cedula', 'nombre', 'comunidad', 'comment', 'timestamp'])
            writer.writeheader()
            writer.writerows(updated_comments)
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Delete comment error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_unsynced_comments():
    """Get all unsynced comments from the log file"""
    comments = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                comments = list(reader)
        except Exception as e:
            app.logger.error(f"Error reading comments: {str(e)}")
    return comments

@app.route('/get_unsynced_comments')
def get_unsynced_comments_api():
    """API endpoint to get unsynced comments"""
    try:
        comments = get_unsynced_comments()
        return jsonify({'comments': comments})
    except Exception as e:
        app.logger.error(f"Get comments error: {str(e)}")
        return jsonify({'error': str(e)}), 500



# Update the save_comment function to include an ID
def save_comment(record_data, comment_text):
    """Save a comment to the log file with an ID"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    comment_id = datetime.now().strftime("%Y%m%d%H%M%S")  # Use timestamp as ID
    
    # Extract key information from record
    cedula = record_data.get('CEDULA', 'N/A')
    nombre = record_data.get('NOMBRE COMPLETO', 'N/A')
    comunidad = record_data.get('COMUNIDAD', 'N/A')
    
    # Append to CSV
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([comment_id, cedula, nombre, comunidad, comment_text, timestamp])

# Database helper functions
def get_database_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        app.logger.error(f"Database connection error: {str(e)}")
        raise

def normalize_string(text):
    """Normalize string for better search matching"""
    if not text:
        return ""
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
        if term in searches[field]:
            searches[field].remove(term)
        searches[field].insert(0, term)
        searches[field] = searches[field][:5]
        
        with open(RECENT_SEARCHES_FILE, 'w', encoding='utf-8') as f:
            json.dump(searches, f, ensure_ascii=False)

def query_database(field, value, filters=None):
    """Query database with optional filters"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Base query
        if field == "NOMBRE COMPLETO":
            # Use LIKE for partial matching
            query = """
            SELECT * FROM records 
            WHERE LOWER([NOMBRE COMPLETO]) LIKE ? 
            OR LOWER([NOMBRE COMPLETO]) LIKE ?
            """
            name_lower = value.lower()
            cursor.execute(query, (f'%{name_lower}%', f'{name_lower}%'))
        else:
            # Exact match for CEDULA and CONTACTO 1
            field_name = f'[{field}]' if field == "CONTACTO 1" else field
            cursor.execute(f"SELECT * FROM records WHERE {field_name} = ?", (value,))
        
        results = [dict(row) for row in cursor.fetchall()]
        
        # Apply filters
        if filters:
            if filters.get('comunidad') and filters['comunidad'] != 'Todas':
                results = [r for r in results if r.get('COMUNIDAD', '').lower() == filters['comunidad'].lower()]
            if filters.get('estado') and filters['estado'] != 'Todos':
                results = [r for r in results if r.get('ESTADO', '').lower() == filters['estado'].lower()]
        
        return results
    finally:
        conn.close()

# Routes
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
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
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
    except Exception as e:
        app.logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/comments')
def view_comments():
    """View all unsynced comments"""
    try:
        comments = get_unsynced_comments()
        return render_template('comments.html', comments=comments)
    except Exception as e:
        app.logger.error(f"View comments error: {str(e)}")
        return render_template('error.html', 
                           error_code=500, 
                           error_message=str(e)), 500

@app.route('/add_comment', methods=['POST'])
def add_comment():
    """Add a comment to a record"""
    try:
        data = request.get_json()
        record_data = data.get('record')
        comment_text = data.get('comment', '').strip()
        
        if not record_data or not comment_text:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        save_comment(record_data, comment_text)
        return jsonify({'success': True, 'message': 'Comentario añadido correctamente'})
    except Exception as e:
        app.logger.error(f"Add comment error: {str(e)}")
        return jsonify({'error': f'Error al guardar comentario: {str(e)}'}), 500

# Replace the existing sync_database function with this one
@app.route('/sync_database', methods=['POST'])
def sync_database():
    """Sync comments with external service and clear local comments"""
    try:
        # Get all unsynced comments
        comments = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                comments = list(reader)

        if comments:
            try:
                # Try to upload comments to external service
                response = requests.post(
                    'https://techodbquery.onrender.com/upload_comments',
                    json={'comments': comments},
                    timeout=10  # 10 seconds timeout
                )
                
                if response.status_code != 200:
                    return jsonify({
                        'success': False,
                        'error': 'Error al cargar comentarios al servidor externo'
                    }), 500

                # If successful, clear the comments file
                with open(LOG_FILE, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['id', 'cedula', 'nombre', 'comunidad', 'comment', 'timestamp'])
                
            except requests.RequestException as e:
                app.logger.error(f"External service error: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': 'Error de conexión con el servidor externo'
                }), 500
        
        return jsonify({
            'success': True, 
            'message': 'Comentarios sincronizados correctamente',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        app.logger.error(f"Sync error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
# Helper functions for comments
def has_unsynced_comments():
    """Check if there are unsynced comments"""
    return os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > len('cedula,nombre,comunidad,comment,timestamp\n')


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

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"500 error: {str(error)}")
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Error interno del servidor"), 500

# Initialize database and required files
init_database()

if __name__ == '__main__':
    # Enable logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run the app in debug mode
    app.run(debug=True, host='0.0.0.0', port=5000)