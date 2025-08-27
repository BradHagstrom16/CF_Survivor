import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-this')
    POOL_TIMEZONE = os.getenv('POOL_TIMEZONE', 'America/Chicago')

class DevelopmentConfig(Config):
    DEBUG = True
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'picks.db')

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/B1GBrad/CF_Survivor/picks.db'
