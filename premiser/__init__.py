from flask import Flask
from .blueprint import BLUEPRINT

app = Flask(__name__)

# app.config['tempdir'] = "/tmp"
app.config.from_envvar('PREMISER_CONFIG', silent=True)

app.register_blueprint(BLUEPRINT)
