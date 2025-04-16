import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from config import FIREBASE_CREDENTIALS_PATH, DEBUG, SECRET_KEY

app = Flask(__name__)
app.config.from_object('config')

cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)

db_firestore = firestore.client()

CORS(app)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks_ref = db_firestore.collection("tasks")
    tasks = tasks_ref.stream()

    task_list = []
    for task in tasks:
        task_data = task.to_dict()
        task_list.append(task_data)

    return jsonify(task_list)

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task_ref = db_firestore.collection("tasks").document(str(task_id))
    task = task_ref.get()

    if task.exists:
        return jsonify(task.to_dict())
    return ('Task not found', 404)

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

    # Add to Firestore collection
    doc_ref = db_firestore.collection("tasks").document()
    doc_ref.set(new_task)

    return jsonify(new_task), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task_ref = db_firestore.collection("tasks").document(str(task_id))
    task = task_ref.get()

    if not task.exists:
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
    task = task_ref.get()

    if not task.exists:
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

    tasks_ref = db_firestore.collection("tasks")
    tasks = tasks_ref.order_by("position").stream()

    task_list = [task.to_dict() for task in tasks]
    index = next((i for i, t in enumerate(task_list) if t['position'] == task.to_dict()['position']), None)

    if direction == "up" and index > 0:
        other_task = task_list[index - 1]
    elif direction == "down" and index < len(task_list) - 1:
        other_task = task_list[index + 1]
    else:
        return ('Invalid move', 400)

    # Swap positions
    task_data = task.to_dict()
    other_task_data = other_task
    task_data['position'], other_task_data['position'] = other_task_data['position'], task_data['position']

    # Update Firestore with new positions
    task_ref.update(task_data)
    tasks_ref.document(str(other_task['position'])).update(other_task_data)

    return jsonify({
        "moved": task_data,
        "swapped_with": other_task_data
    })

if __name__ == '__main__':
    app.run(debug=True)
