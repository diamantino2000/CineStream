import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, make_response

app = Flask(__name__)

# --- RUTA PRINCIPAL ---
@app.route('/')
def home():
    return render_template('index.html')

# Límite de subida: 16 GB por archivo
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024 

UPLOAD_FOLDER_VIDEOS = 'static/uploads/videos'
UPLOAD_FOLDER_COVERS = 'static/uploads/covers'
DB_FILE = 'database.json'

ALLOWED_VIDEO_EXT = {'mkv', 'mp4', 'm4v', 'avi'}
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'webp', 'jfif', 'pjp', 'pjpeg'}

app.config['UPLOAD_FOLDER_VIDEOS'] = UPLOAD_FOLDER_VIDEOS
app.config['UPLOAD_FOLDER_COVERS'] = UPLOAD_FOLDER_COVERS

os.makedirs(UPLOAD_FOLDER_VIDEOS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_COVERS, exist_ok=True)

def load_db():
    if not os.path.exists(DB_FILE):
        initial_data = {"movies": [], "series": []}
        save_db(initial_data)
        return initial_data
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "movies" not in data: data["movies"] = []
            if "series" not in data: data["series"] = []
            return data
    except Exception as e:
        print(f"⚠️ Error al leer database.json: {e}")
        return {"movies": [], "series": []}

def save_db(data):
    try:
        temp_file = f"{DB_FILE}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(temp_file, DB_FILE)
    except Exception as e:
        print(f"❌ Error al guardar database.json: {e}")

def allowed_file(filename, allowed_set):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].strip().lower()
    return ext in allowed_set

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/media', methods=['GET'])
def get_media():
    db_data = load_db()
    for s in db_data.get("series", []):
        if "episodes" in s:
            s["episodes"].sort(key=lambda x: (int(x.get("season", 1)), int(x.get("ep_num", 1))))
            
    response = make_response(jsonify(db_data))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/upload/movie', methods=['POST'])
def upload_movie():
    try:
        title = request.form.get('title', '').strip()
        cover_file = request.files.get('cover')
        video_file = request.files.get('video')

        if not title or not cover_file or not video_file:
            return jsonify({"error": "Faltan datos obligatorios"}), 400

        if allowed_file(cover_file.filename, ALLOWED_IMAGE_EXT) and \
           allowed_file(video_file.filename, ALLOWED_VIDEO_EXT):
            
            unique_id = uuid.uuid4().hex
            cover_ext = cover_file.filename.rsplit('.', 1)[1].lower()
            video_ext = video_file.filename.rsplit('.', 1)[1].lower()

            cover_filename = f"{unique_id}.{cover_ext}"
            video_filename = f"{unique_id}.{video_ext}"

            cover_path = os.path.join(app.config['UPLOAD_FOLDER_COVERS'], cover_filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER_VIDEOS'], video_filename)

            cover_file.save(cover_path)
            video_file.save(video_path)

            db = load_db()
            new_movie = {
                "id": unique_id,
                "title": title,
                "cover_url": f"/static/uploads/covers/{cover_filename}",
                "video_url": f"/static/uploads/videos/{video_filename}",
                "ext": video_ext.upper()
            }
            db["movies"].append(new_movie)
            save_db(db)

            return jsonify({"success": True, "item": new_movie}), 200

        return jsonify({"error": "Formato de archivo no permitido"}), 400

    except Exception as e:
        return jsonify({"error": f"Error en el servidor: {str(e)}"}), 500

@app.route('/upload/series', methods=['POST'])
def upload_series():
    try:
        title = request.form.get('title', '').strip()
        season = int(request.form.get('season', 1))
        ep_num = int(request.form.get('ep_num', 1))
        ep_title = request.form.get('ep_title', '').strip() or f"Episodio {ep_num}"
        
        cover_file = request.files.get('cover')
        video_file = request.files.get('video')

        if not title or not video_file:
            return jsonify({"error": "El título y el video son obligatorios"}), 400

        if allowed_file(video_file.filename, ALLOWED_VIDEO_EXT):
            unique_id = uuid.uuid4().hex
            video_ext = video_file.filename.rsplit('.', 1)[1].lower()
            video_filename = f"{unique_id}.{video_ext}"
            video_path = os.path.join(app.config['UPLOAD_FOLDER_VIDEOS'], video_filename)
            video_file.save(video_path)

            db = load_db()
            series_item = next((s for s in db["series"] if s["title"].lower() == title.lower()), None)

            cover_url = ""
            if cover_file and allowed_file(cover_file.filename, ALLOWED_IMAGE_EXT):
                cover_ext = cover_file.filename.rsplit('.', 1)[1].lower()
                cover_filename = f"{unique_id}.{cover_ext}"
                cover_path = os.path.join(app.config['UPLOAD_FOLDER_COVERS'], cover_filename)
                cover_file.save(cover_path)
                cover_url = f"/static/uploads/covers/{cover_filename}"

            new_episode = {
                "id": unique_id,
                "season": season,
                "ep_num": ep_num,
                "ep_title": ep_title,
                "video_url": f"/static/uploads/videos/{video_filename}"
            }

            if series_item:
                if cover_url:
                    series_item["cover_url"] = cover_url
                series_item["episodes"] = [ep for ep in series_item["episodes"] if not (ep.get("season") == season and ep.get("ep_num") == ep_num)]
                series_item["episodes"].append(new_episode)
            else:
                new_series = {
                    "id": uuid.uuid4().hex,
                    "title": title,
                    "cover_url": cover_url or "/static/uploads/covers/default.jpg",
                    "episodes": [new_episode]
                }
                db["series"].append(new_series)

            save_db(db)
            return jsonify({"success": True}), 200

        return jsonify({"error": "Formato de video no permitido"}), 400

    except Exception as e:
        return jsonify({"error": f"Error en el servidor: {str(e)}"}), 500

@app.route('/edit/movie/<movie_id>', methods=['POST'])
def edit_movie(movie_id):
    try:
        new_title = request.json.get('title', '').strip()
        if not new_title:
            return jsonify({"error": "Título inválido"}), 400
        
        db = load_db()
        for m in db["movies"]:
            if m["id"] == movie_id:
                m["title"] = new_title
                break
        save_db(db)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/edit/series/<series_id>', methods=['POST'])
def edit_series(series_id):
    try:
        new_title = request.json.get('title', '').strip()
        if not new_title:
            return jsonify({"error": "Título inválido"}), 400
        
        db = load_db()
        for s in db["series"]:
            if s["id"] == series_id:
                s["title"] = new_title
                break
        save_db(db)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete/series/<series_id>', methods=['DELETE'])
def delete_series(series_id):
    try:
        db = load_db()
        db["series"] = [s for s in db["series"] if s["id"] != series_id]
        save_db(db)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete/movie/<movie_id>', methods=['DELETE'])
def delete_movie(movie_id):
    try:
        db = load_db()
        db["movies"] = [m for m in db["movies"] if m["id"] != movie_id]
        save_db(db)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
