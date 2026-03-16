# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
import pymysql
# Import Flask 
from flask import Flask
from dotenv import load_dotenv
load_dotenv()

# Inject Flask magic
app = Flask(__name__)

app.secret_key = 'oiewagbew193409pfj'


db_connection = pymysql.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False
)
cursor = db_connection.cursor()

# Import routing to render the pages
from app import views
