import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# Ruta principal
@app.route('/')
def home():
    return render_template('index.html')

# Ruta dinámica para películas
@app.route('/pelicula/<media_id>')
def pelicula_detalle(media_id):
    # Flask renderizará el mismo diseño, pasando la ID de la película
    return render_template('index.html', media_id=media_id, media_type='movies')

# Ruta dinámica para series
@app.route('/serie/<media_id>')
def serie_detalle(media_id):
    return render_template('index.html', media_id=media_id, media_type='series')

if __name__ == '__main__':
    app.run(debug=True)

COVERS_FOLDER = os.path.join('static', 'uploads', 'covers')
VIDEOS_FOLDER = os.path.join('static', 'uploads', 'videos')
DB_FILE = 'database.json'

os.makedirs(COVERS_FOLDER, exist_ok=True)
os.makedirs(VIDEOS_FOLDER, exist_ok=True)

def load_catalog():
    if not os.path.exists(DB_FILE):
        return {"movies": [], "series": []}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"movies": data, "series": []}
            return data
    except Exception:
        return {"movies": [], "series": []}

def save_catalog(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/media')
def get_media():
    catalog = load_catalog()
    return jsonify(catalog)

@app.route('/stream/<path:filename>')
def stream_video(filename):
    return send_from_directory(VIDEOS_FOLDER, filename)

# --- RUTAS DE PELÍCULAS ---
@app.route('/upload/movie', methods=['POST'])
def upload_movie():
    title = request.form.get('title')
    video_url = request.form.get('video_url', '').strip()
    cover_file = request.files.get('cover')
    video_file = request.files.get('video')

    if not title or not cover_file:
        return jsonify({'success': False, 'error': 'Faltan datos obligatorios'}), 400

    cover_name = cover_file.filename
    cover_path = os.path.join(COVERS_FOLDER, cover_name)
    cover_file.save(cover_path)

    video_filename = None
    if video_file and video_file.filename:
        video_filename = video_file.filename
        video_path = os.path.join(VIDEOS_FOLDER, video_filename)
        video_file.save(video_path)

    catalog = load_catalog()
    new_movie = {
        "id": str(len(catalog.get('movies', [])) + 1),
        "title": title,
        "cover_url": f"/static/uploads/covers/{cover_name}",
        "video_url": video_url if video_url else (f"/stream/{video_filename}" if video_filename else "")
    }

    catalog['movies'].append(new_movie)
    save_catalog(catalog)
    return jsonify({'success': True})

@app.route('/edit/movie/<id_pelicula>', methods=['POST'])
def edit_movie(id_pelicula):
    data = request.get_json()
    new_title = data.get('title')
    catalog = load_catalog()
    for m in catalog.get('movies', []):
        if str(m.get('id')) == str(id_pelicula):
            m['title'] = new_title
            break
    save_catalog(catalog)
    return jsonify({'success': True})

@app.route('/delete/movie/<id_pelicula>', methods=['DELETE'])
def delete_movie(id_pelicula):
    catalog = load_catalog()
    catalog['movies'] = [m for m in catalog.get('movies', []) if str(m.get('id')) != str(id_pelicula)]
    save_catalog(catalog)
    return jsonify({'success': True})

# --- RUTAS DE SERIES ---
@app.route('/upload/series', methods=['POST'])
def upload_series():
    catalog = load_catalog()
    title = request.form.get('title')
    season = int(request.form.get('season', 1))
    ep_num = int(request.form.get('ep_num', 1))
    ep_title = request.form.get('ep_title', f'Episodio {ep_num}')
    video_filename = request.form.get('video_filename') or request.form.get('video')
    cover_file = request.files.get('cover')

    # Buscar serie existente
    series_item = next((s for s in catalog['series'] if s['title'].lower() == title.lower()), None)

    if not series_item:
        cover_url = ""
        if cover_file:
            cover_name = cover_file.filename
            cover_file.save(os.path.join(COVERS_FOLDER, cover_name))
            cover_url = f"/static/uploads/covers/{cover_name}"
        
        series_item = {
            "id": str(len(catalog['series']) + 1),
            "title": title,
            "cover_url": cover_url,
            "episodes": []
        }
        catalog['series'].append(series_item)

    nuevo_ep = {
        "season": season,
        "ep_num": ep_num,
        "ep_title": ep_title,
        "video_url": f"/stream/{video_filename}" if video_filename else ""
    }
    series_item['episodes'].append(nuevo_ep)
    save_catalog(catalog)
    return jsonify({'success': True})

if __name__ == '__main__':
    print("🎬 CineStream Local ejecutándose en http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
