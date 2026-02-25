import os

class Config:
    SECRET_KEY = "supersecretkey"
    SQLALCHEMY_DATABASE_URI = "sqlite:///surge.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False