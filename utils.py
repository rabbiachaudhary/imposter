import random
import string
from config import get_connection

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

def assign_words(code):
    conn = get_connection()
    cursor = conn.cursor()

    # Example words (replace with Groq API integration later)
    word_pool = [
        ("desert", "beach"),
        ("apple", "banana"),
        ("sun", "moon"),
        ("rocket", "spaceship")
    ]
    correct_word, impostor_word = random.choice(word_pool)

    cursor.execute("SELECT username FROM users WHERE game_code=%s", (code,))
    users = cursor.fetchall()
    usernames = [u['username'] for u in users]


    impostor = random.choice(usernames)
    for user in usernames:
        word = impostor_word if user == impostor else correct_word
        cursor.execute("UPDATE users SET assigned_word=%s, is_impostor=%s WHERE username=%s AND game_code=%s",
                       (word, user == impostor, user, code))
    cursor.execute("UPDATE games SET status='in_progress' WHERE code=%s", (code,))
    conn.commit()
    conn.close()
