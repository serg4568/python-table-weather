import os
from flask import Flask, render_template, request, jsonify

# Определяем путь к папке templates на один уровень выше папки api/
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

@app.route("/")
def index():
    return render_template("index.html")

# Остальной ваш код...