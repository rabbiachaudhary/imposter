import pymysql

import random
import string

def connect_db():
    return pymysql.connector.connect(
        host="localhost",
        user="root",
        password="662373+azra-azra",
        database="word_imposter"
    )

def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))