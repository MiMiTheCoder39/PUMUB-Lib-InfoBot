"""
models/db.py
------------
Flask-MySQLdb ကို initialize လုပ်ပေးတဲ့ module.
app.py ထဲမှာ mysql.init_app(app) ခေါ်ပြီးသုံးပါမယ်။
Routes/Models တွေက "from models.db import mysql" လို့ import လုပ်ပြီး
mysql.connection.cursor() ကို သုံးနိုင်ပါတယ်။
"""

from flask_mysqldb import MySQL

mysql = MySQL()
