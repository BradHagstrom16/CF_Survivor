"""
Configuration settings for different environments
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-this')
    POOL_TIMEZONE = os.getenv('POOL_TIMEZONE', 'America/Chicago')
    
class DevelopmentConfig(Config):
    """Development configuration - your local computer"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///picks.db'
    
class ProductionConfig(Config):
    """Production configuration - PythonAnywhere"""
    DEBUG = False
    # PythonAnywhere requires full path
    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/B1GBRAD/CF_Survivor/instance/picks.db'
