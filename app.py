import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS

from dotenv import load_dotenv
load_dotenv() 

app = Flask(__name__)
CORS(app)

app.secret_key = os.getenv('SECRET_KEY', 'default-secret')
app.debug = os.getenv('DEBUG', 'False').lower() in ['true', '1']

firebase_key_path = os.getenv('FIREBASE_CREDENTIALS_PATH')

firebase_key_base64 = os.getenv('FIREBASE_KEY_BASE64')

if firebase_key_base64:
    firebase_key_json = base64.b64decode(firebase_key_base64).decode('utf-8')
    cred = credentials.Certificate(json.loads(firebase_key_json))
elif firebase_key_path:
    cred = credentials.Certificate(firebase_key_path)
else:
    raise ValueError("Firebase credentials not provided!")

firebase_admin.initialize_app(cred)
db_firestore = firestore.client()

# ==== API Routes ====

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Flask Todo API is live!"})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks_ref = db_firestore.collection("tasks")
    tasks = tasks_ref.stream()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task_ref = db_firestore.collection("tasks").document(str(task_id))
    task = task_ref.get()
    return jsonify(task.to_dict()) if task.exists else ('Task not found', 404)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    new_task = {
        "text": data['text'],
        "priority": data.get('priority', 'medium'),
        "dueDate": data.get('dueDate'),
        "completed": data.get('completed', False),
        "position": data.get('position', 0)
    }
    db_firestore.collection("tasks").document().set(new_task)
    return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task_ref = db_firestore.collection("tasks").document(str(task_id))
    if not task_ref.get().exists:
        return ('Task not found', 404)

    data = request.json
    updated_task = {
        "text": data['text'],
        "priority": data['priority'],
        "dueDate": data.get('dueDate'),
        "completed": data['completed'],
        "position": data.get('position', 0)
    }

    task_ref.update(updated_task)
    return jsonify(updated_task)

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task_ref = db_firestore.collection("tasks").document(str(task_id))
    if not task_ref.get().exists:
        return ('Task not found', 404)

    task_ref.delete()
    return ('', 204)

@app.route('/api/tasks/<int:task_id>/toggle', methods=['PATCH'])
def toggle_task(task_id):
    task_ref = db_firestore.collection("tasks").document(str(task_id))
    task = task_ref.get()
    if not task.exists:
        return ('Task not found', 404)

    task_data = task.to_dict()
    task_data['completed'] = not task_data['completed']
    task_ref.update(task_data)
    return jsonify(task_data)

@app.route('/api/tasks/<int:task_id>/move', methods=['POST'])
def move_task(task_id):
    direction = request.json.get("direction")
    task_ref = db_firestore.collection("tasks").document(str(task_id))
    task = task_ref.get()
    if not task.exists:
        return ('Task not found', 404)

    task_data = task.to_dict()
    tasks = db_firestore.collection("tasks").order_by("position").stream()
    task_list = [t.to_dict() for t in tasks]

    index = next((i for i, t in enumerate(task_list) if t['position'] == task_data['position']), None)

    if direction == "up" and index > 0:
        other_task = task_list[index - 1]
    elif direction == "down" and index < len(task_list) - 1:
        other_task = task_list[index + 1]
    else:
        return ('Invalid move', 400)

    # Swap positions
    task_data['position'], other_task['position'] = other_task['position'], task_data['position']
    task_ref.update(task_data)

    # Find and update the other task by its position
    for doc in db_firestore.collection("tasks").stream():
        if doc.to_dict()['position'] == other_task['position']:
            db_firestore.collection("tasks").document(doc.id).update(other_task)
            break

    return jsonify({"moved": task_data, "swapped_with": other_task})

# ==== Run the App ====
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0",port=port,debug=app.debug)
