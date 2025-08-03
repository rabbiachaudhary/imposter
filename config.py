# config.py
import pymysql

def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="662373+azra-azra",
        database="word_impostor_game",
        cursorclass=pymysql.cursors.DictCursor 
          # Optional: makes results easier to work with
    )
