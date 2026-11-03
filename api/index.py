import os
from flask import Flask, render_template, request, jsonify

# Указываем путь к templates относительно текущего файла
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)