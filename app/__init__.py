from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

myapp = Flask(__name__)
myapp.config.from_object(Config)
db = SQLAlchemy(myapp)
migrate = Migrate(myapp, db)

from app import routes, models