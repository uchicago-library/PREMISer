from flask import Flask
from .blueprint import BLUEPRINT

app = Flask(__name__)

# app.config['tempdir'] = "/tmp"

app.register_blueprint(BLUEPRINT)
