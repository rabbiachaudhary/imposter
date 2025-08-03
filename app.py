import streamlit as st
import random
import json
from groq import Groq
import time
import sqlite3
import threading
from datetime import datetime, timedelta

# Database setup
DB_NAME = "imposter_game.db"
db_lock = threading.Lock()

def init_database():
    """Initialize the SQLite database"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Games table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                host TEXT NOT NULL,
                started BOOLEAN DEFAULT FALSE,
                phase TEXT DEFAULT 'lobby',
                main_word TEXT,
                imposter_word TEXT,
                imposter TEXT,
                discussion_ended BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Players table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                player_name TEXT,
                word TEXT,
                is_imposter BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (game_id) REFERENCES games (game_id),
                UNIQUE(game_id, player_name)
            )
        ''')
        
        # Discussion words table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discussion_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                player_name TEXT,
                word TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games (game_id)
            )
        ''')
        
        # Votes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                voter TEXT,
                suspect TEXT,
                FOREIGN KEY (game_id) REFERENCES games (game_id),
                UNIQUE(game_id, voter)
            )
        ''')
        
        conn.commit()
        conn.close()

def cleanup_old_games():
    """Remove games older than 24 hours"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        cursor.execute("DELETE FROM games WHERE created_at < ?", (cutoff_time,))
        cursor.execute("DELETE FROM players WHERE game_id NOT IN (SELECT game_id FROM games)")
        cursor.execute("DELETE FROM discussion_words WHERE game_id NOT IN (SELECT game_id FROM games)")
        cursor.execute("DELETE FROM votes WHERE game_id NOT IN (SELECT game_id FROM games)")
        
        conn.commit()
        conn.close()

# Initialize Groq client
def init_groq_client():
    if 'groq_client' not in st.session_state:
        # You need to set your Groq API key here
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            st.error("Please set your Groq API key in Streamlit secrets!")
            st.stop()
        st.session_state.groq_client = Groq(api_key=api_key)

def generate_words_with_groq():
    """Generate a normal word and an imposter word using Groq API"""
    try:
        client = st.session_state.groq_client
        
        # Generate main word
        main_word_prompt = "Generate a single common noun (one word only) that people can easily describe with related words. Examples: apple, car, book, tree. Just return the word, nothing else."
        
        main_response = client.chat.completions.create(
            messages=[
                {"role": "user", "content": main_word_prompt}
            ],
            model="llama3-8b-8192",
            temperature=0.8,
            max_tokens=10
        )
        
        main_word = main_response.choices[0].message.content.strip().lower()
        
        # Generate imposter word (related but different)
        imposter_prompt = f"Generate a single word that is somewhat related to '{main_word}' but different enough that someone describing it would seem suspicious. Just return the word, nothing else."
        
        imposter_response = client.chat.completions.create(
            messages=[
                {"role": "user", "content": imposter_prompt}
            ],
            model="llama3-8b-8192",
            temperature=0.9,
            max_tokens=10
        )
        
        imposter_word = imposter_response.choices[0].message.content.strip().lower()
        
        return main_word, imposter_word
    
    except Exception as e:
        st.error(f"Error generating words: {e}")
        # Fallback words if API fails
        word_pairs = [
            ("apple", "orange"),
            ("car", "bicycle"),
            ("cat", "dog"),
            ("book", "magazine"),
            ("tree", "flower")
        ]
        return random.choice(word_pairs)

# Database operations
def create_game_in_db(game_id, host_name):
    """Create a new game in the database"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO games (game_id, host)
                VALUES (?, ?)
            ''', (game_id, host_name))
            
            cursor.execute('''
                INSERT INTO players (game_id, player_name)
                VALUES (?, ?)
            ''', (game_id, host_name))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

def join_game_in_db(game_id, player_name):
    """Join an existing game in the database"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if game exists and not started
        cursor.execute("SELECT started FROM games WHERE game_id = ?", (game_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, "Game not found!"
        
        if result[0]:
            conn.close()
            return False, "Game already started!"
        
        try:
            cursor.execute('''
                INSERT INTO players (game_id, player_name)
                VALUES (?, ?)
            ''', (game_id, player_name))
            conn.commit()
            conn.close()
            return True, "Joined successfully!"
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Player name already taken in this game!"

def get_game_players(game_id):
    """Get all players in a game"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT player_name FROM players WHERE game_id = ?", (game_id,))
        players = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return players

def get_game_info(game_id):
    """Get game information"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                'game_id': result[0],
                'host': result[1],
                'started': bool(result[2]),
                'phase': result[3],
                'main_word': result[4],
                'imposter_word': result[5],
                'imposter': result[6],
                'discussion_ended': bool(result[7])
            }
        return None

def start_game_in_db(game_id):
    """Start the game and assign words"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get players
        cursor.execute("SELECT player_name FROM players WHERE game_id = ?", (game_id,))
        players = [row[0] for row in cursor.fetchall()]
        
        if len(players) < 3:
            conn.close()
            return False, "Need at least 3 players to start!"
        
        # Generate words using Groq
        main_word, imposter_word = generate_words_with_groq()
        
        # Choose random imposter
        imposter = random.choice(players)
        
        # Update game
        cursor.execute('''
            UPDATE games 
            SET started = TRUE, phase = 'discussion', main_word = ?, imposter_word = ?, imposter = ?
            WHERE game_id = ?
        ''', (main_word, imposter_word, imposter, game_id))
        
        # Assign words to players
        for player in players:
            word = imposter_word if player == imposter else main_word
            is_imposter = player == imposter
            cursor.execute('''
                UPDATE players 
                SET word = ?, is_imposter = ?
                WHERE game_id = ? AND player_name = ?
            ''', (word, is_imposter, game_id, player))
        
        conn.commit()
        conn.close()
        return True, "Game started!"

def get_player_word(game_id, player_name):
    """Get a player's assigned word"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT word FROM players WHERE game_id = ? AND player_name = ?", (game_id, player_name))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None

def add_discussion_word_to_db(game_id, player_name, word):
    """Add a discussion word to the database"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO discussion_words (game_id, player_name, word)
            VALUES (?, ?, ?)
        ''', (game_id, player_name, word))
        
        conn.commit()
        conn.close()

def get_discussion_words(game_id):
    """Get all discussion words for a game"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT player_name, word 
            FROM discussion_words 
            WHERE game_id = ? 
            ORDER BY timestamp
        ''', (game_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Group by player
        discussion_words = {}
        for player_name, word in results:
            if player_name not in discussion_words:
                discussion_words[player_name] = []
            discussion_words[player_name].append(word)
        
        return discussion_words

def update_game_phase(game_id, phase):
    """Update the game phase"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE games SET phase = ? WHERE game_id = ?", (phase, game_id))
        conn.commit()
        conn.close()

def add_vote_to_db(game_id, voter, suspect):
    """Add a vote to the database"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO votes (game_id, voter, suspect)
            VALUES (?, ?, ?)
        ''', (game_id, voter, suspect))
        
        conn.commit()
        conn.close()

def get_votes(game_id):
    """Get all votes for a game"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT voter, suspect FROM votes WHERE game_id = ?", (game_id,))
        votes = dict(cursor.fetchall())
        
        conn.close()
        return votes

def get_voting_results(game_id):
    """Get the voting results"""
    game_info = get_game_info(game_id)
    votes = get_votes(game_id)
    
    if not votes or not game_info:
        return None
    
    # Count votes
    vote_counts = {}
    for suspect in votes.values():
        vote_counts[suspect] = vote_counts.get(suspect, 0) + 1
    
    # Find the player with most votes
    suspected_imposter = max(vote_counts, key=vote_counts.get)
    actual_imposter = game_info['imposter']
    
    return {
        'suspected_imposter': suspected_imposter,
        'actual_imposter': actual_imposter,
        'vote_counts': vote_counts,
        'imposter_caught': suspected_imposter == actual_imposter,
        'main_word': game_info['main_word'],
        'imposter_word': game_info['imposter_word']
    }

def reset_game_in_db(game_id):
    """Reset game for a new round"""
    with db_lock:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Reset game
        cursor.execute('''
            UPDATE games 
            SET started = FALSE, phase = 'lobby', main_word = NULL, 
                imposter_word = NULL, imposter = NULL, discussion_ended = FALSE
            WHERE game_id = ?
        ''', (game_id,))
        
        # Reset players
        cursor.execute('''
            UPDATE players 
            SET word = NULL, is_imposter = FALSE
            WHERE game_id = ?
        ''', (game_id,))
        
        # Clear discussion words and votes
        cursor.execute("DELETE FROM discussion_words WHERE game_id = ?", (game_id,))
        cursor.execute("DELETE FROM votes WHERE game_id = ?", (game_id,))
        
        conn.commit()
        conn.close()

# Initialize session state
def init_session_state():
    if 'game_state' not in st.session_state:
        st.session_state.game_state = 'menu'
    if 'current_game_id' not in st.session_state:
        st.session_state.current_game_id = None
    if 'player_name' not in st.session_state:
        st.session_state.player_name = ""
    if 'is_host' not in st.session_state:
        st.session_state.is_host = False

def create_game_id():
    """Generate a 4-digit game ID"""
    return str(random.randint(1000, 9999))

# Main app
def main():
    st.set_page_config(page_title="Imposter Word Game", page_icon="🕵️", layout="wide")
    
    # Initialize everything
    init_database()
    cleanup_old_games()
    init_groq_client()
    init_session_state()
    
    st.title("🕵️ Imposter Word Game")
    
    # Sidebar for game info
    with st.sidebar:
        st.header("Game Info")
        if st.session_state.current_game_id:
            st.write(f"**Game ID:** {st.session_state.current_game_id}")
            st.write(f"**Player:** {st.session_state.player_name}")
            
            players = get_game_players(st.session_state.current_game_id)
            st.write(f"**Players:** {len(players)}")
            st.write("**Player List:**")
            for player in players:
                st.write(f"- {player}")
        
        if st.button("🏠 Back to Menu"):
            st.session_state.game_state = 'menu'
            st.session_state.current_game_id = None
            st.session_state.is_host = False
            st.rerun()
    
    # Main game logic
    if st.session_state.game_state == 'menu':
        show_menu()
    elif st.session_state.game_state == 'lobby':
        show_lobby()
    elif st.session_state.game_state == 'game':
        show_game()

def show_menu():
    """Show the main menu"""
    st.header("Welcome to Imposter Word Game!")
    st.write("Play with friends across different devices!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎮 Create Game")
        with st.form("create_game"):
            host_name = st.text_input("Your Name:", key="host_name_input")
            if st.form_submit_button("Create Game", type="primary"):
                if host_name.strip():
                    game_id = create_game_id()
                    while not create_game_in_db(game_id, host_name.strip()):
                        game_id = create_game_id()
                    
                    st.session_state.current_game_id = game_id
                    st.session_state.player_name = host_name.strip()
                    st.session_state.is_host = True
                    st.session_state.game_state = 'lobby'
                    st.success(f"Game created! Game ID: {game_id}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please enter your name!")
    
    with col2:
        st.subheader("🚪 Join Game")
        with st.form("join_game"):
            player_name = st.text_input("Your Name:", key="player_name_input")
            game_id = st.text_input("Game ID:", key="game_id_input")
            if st.form_submit_button("Join Game", type="primary"):
                if player_name.strip() and game_id.strip():
                    success, message = join_game_in_db(game_id.strip(), player_name.strip())
                    if success:
                        st.session_state.current_game_id = game_id.strip()
                        st.session_state.player_name = player_name.strip()
                        st.session_state.is_host = False
                        st.session_state.game_state = 'lobby'
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please enter your name and game ID!")

def show_lobby():
    """Show the game lobby"""
    game_id = st.session_state.current_game_id
    game_info = get_game_info(game_id)
    
    if not game_info:
        st.error("Game not found!")
        st.session_state.game_state = 'menu'
        st.rerun()
        return
    
    st.header(f"Game Lobby - {game_id}")
    st.write(f"Host: {game_info['host']}")
    
    # Show players
    players = get_game_players(game_id)
    st.subheader(f"Players ({len(players)}):")
    for i, player in enumerate(players, 1):
        st.write(f"{i}. {player}")
    
    # Start game (only host can start)
    if st.session_state.is_host and not game_info['started']:
        if st.button("🚀 Start Game", type="primary"):
            success, message = start_game_in_db(game_id)
            if success:
                st.session_state.game_state = 'game'
                st.success(message)
                time.sleep(1)
                st.rerun()
            else:
                st.error(message)
    
    # Check if game started (for non-hosts)
    if not st.session_state.is_host and game_info['started']:
        st.session_state.game_state = 'game'
        st.rerun()
    
    # Auto refresh every 2 seconds
    time.sleep(2)
    st.rerun()

def show_game():
    """Show the main game interface"""
    game_id = st.session_state.current_game_id
    game_info = get_game_info(game_id)
    player_name = st.session_state.player_name
    
    if not game_info:
        st.error("Game not found!")
        st.session_state.game_state = 'menu'
        st.rerun()
        return
    
    if game_info['phase'] == 'discussion':
        show_discussion_phase(game_info, game_id, player_name)
    elif game_info['phase'] == 'voting':
        show_voting_phase(game_info, game_id, player_name)
    elif game_info['phase'] == 'results':
        show_results_phase(game_info, game_id)

def show_discussion_phase(game_info, game_id, player_name):
    """Show the discussion phase"""
    st.header("🎯 Your Word")
    
    # Show player's word
    player_word = get_player_word(game_id, player_name)
    if player_word:
        st.success(f"Your word is: **{player_word.upper()}**")
    
    st.header("💬 Discussion Phase")
    st.write("Drop words related to your word. Try to figure out who the imposter is!")
    
    # Add word form
    with st.form("add_word"):
        new_word = st.text_input("Add a related word:")
        if st.form_submit_button("Add Word"):
            if new_word.strip():
                add_discussion_word_to_db(game_id, player_name, new_word.strip())
                st.success(f"Added word: {new_word}")
                time.sleep(1)
                st.rerun()
    
    # Show all discussion words
    st.header("📝 Discussion Words")
    discussion_words = get_discussion_words(game_id)
    players = get_game_players(game_id)
    
    for player in players:
        words = discussion_words.get(player, [])
        with st.expander(f"{player} ({len(words)} words)"):
            if words:
                for word in words:
                    st.write(f"• {word}")
            else:
                st.write("No words yet...")
    
    # Voting to continue or start voting (Host only controls)
    st.header("🗳️ Decision Time")
    
    if st.session_state.is_host:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Continue Discussion", key="continue_discussion"):
                st.info("Continue adding words...")
        
        with col2:
            if st.button("Start Voting Phase", key="start_voting", type="primary"):
                update_game_phase(game_id, 'voting')
                st.rerun()
    else:
        st.info("⏳ Waiting for host to start voting phase...")
        # Check if phase changed to voting
        current_game_info = get_game_info(game_id)
        if current_game_info and current_game_info['phase'] == 'voting':
            st.rerun()
    
    # Auto refresh every 3 seconds to show new words and phase changes
    time.sleep(3)
    st.rerun()

def show_voting_phase(game_info, game_id, player_name):
    """Show the voting phase"""
    st.header("🗳️ Voting Phase")
    st.write("Vote for who you think is the imposter!")
    
    # Voting form
    players = get_game_players(game_id)
    other_players = [p for p in players if p != player_name]
    
    with st.form("vote_form"):
        suspect = st.selectbox("Who do you think is the imposter?", other_players)
        
        if st.form_submit_button("Cast Vote", type="primary"):
            add_vote_to_db(game_id, player_name, suspect)
            st.success(f"You voted for: {suspect}")
            time.sleep(1)
            st.rerun()
    
    # Show voting status
    st.header("📊 Voting Status")
    votes = get_votes(game_id)
    total_players = len(players)
    votes_cast = len(votes)
    
    st.write(f"Votes cast: {votes_cast}/{total_players}")
    
    # Show who has voted (without revealing votes)
    for player in players:
        status = "✅ Voted" if player in votes else "⏳ Waiting"
        st.write(f"{player}: {status}")
    
    # Show results when everyone voted (Host only)
    if votes_cast == total_players:
        if st.session_state.is_host:
            if st.button("📊 Show Results", type="primary"):
                update_game_phase(game_id, 'results')
                st.rerun()
        else:
            st.info("⏳ Waiting for host to show results...")
            # Check if phase changed to results
            current_game_info = get_game_info(game_id)
            if current_game_info and current_game_info['phase'] == 'results':
                st.rerun()
    
    # Auto refresh every 3 seconds to show new votes and phase changes
    time.sleep(3)
    st.rerun()

def show_results_phase(game_info, game_id):
    """Show the game results"""
    st.header("🎉 Game Results")
    
    results = get_voting_results(game_id)
    
    if results:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 The Words")
            st.write(f"**Normal word:** {results['main_word']}")
            st.write(f"**Imposter word:** {results['imposter_word']}")
        
        with col2:
            st.subheader("🕵️ The Imposter")
            st.write(f"**Actual imposter:** {results['actual_imposter']}")
            st.write(f"**Suspected imposter:** {results['suspected_imposter']}")
        
        # Results
        if results['imposter_caught']:
            st.success("🎉 The imposter was caught! Regular players win!")
        else:
            st.error("😈 The imposter escaped! Imposter wins!")
        
        # Voting breakdown
        st.subheader("📊 Vote Breakdown")
        for suspect, count in results['vote_counts'].items():
            st.write(f"{suspect}: {count} votes")
        
        # Show discussion words
        st.subheader("💭 Discussion Words")
        discussion_words = get_discussion_words(game_id)
        for player, words in discussion_words.items():
            is_imposter = " (IMPOSTER)" if player == results['actual_imposter'] else ""
            st.write(f"**{player}{is_imposter}:** {', '.join(words) if words else 'No words'}")
    
    # New game button
    if st.button("🎮 New Game"):
        # Reset game
        if st.session_state.is_host:
            reset_game_in_db(game_id)
            st.session_state.game_state = 'lobby'
        else:
            st.session_state.game_state = 'menu'
        st.rerun()

if __name__ == "__main__":
    main()