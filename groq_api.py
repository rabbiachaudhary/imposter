import random
def get_words():
    # Replace this with real Groq API logic
    words = ["ocean", "mountain", "pencil", "bicycle", "fire"]
    base_word = random.choice(words)
    imposter_word = random.choice([w for w in words if w != base_word])
    return base_word, imposter_word
