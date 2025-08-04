# 🕵️ Imposter Word Game

🎯 Live App: https://wordimposter.streamlit.app/

Imposter is a real-time multiplayer word-guessing game where players must deduce who among them is the "imposter." The game is built with Streamlit and uses the Groq API to dynamically generate related words, ensuring a unique experience every round.

## How to Play

1.  **Create or Join a Game:** One player creates a game and shares the 4-digit Game ID with friends. Other players use this ID to join the lobby.
2.  **Receive Your Word:** Once the host starts the game, every player receives a secret word. All players receive the same word, except for one—the Imposter—who gets a closely related but different word.
3.  **Discussion Phase:** Players take turns submitting single words related to their secret word. The goal for the regular players is to prove they know the secret word without giving it away. The Imposter's goal is to blend in by guessing the theme from other players' clues and submitting plausible words.
4.  **Voting Phase:** After the discussion, everyone votes for the player they suspect is the Imposter.
5.  **Results:**
    *   If the Imposter is correctly voted out, the regular players win.
    *   If the players vote for an innocent player, the Imposter wins.

## Features

*   **Real-time Multiplayer:** Play with friends seamlessly across different devices.
*   **Dynamic Word Generation:** Leverages the Groq API (Llama 3) to generate a unique pair of a main word and an imposter word for each game.
*   **Persistent Game State:** Uses a simple SQLite database to manage game sessions, players, and progress.
*   **Easy Deployment:** Fully containerized with a Dev Container configuration for one-click setup in environments like GitHub Codespaces.
*   **Automatic Cleanup:** Old game data (older than 24 hours) is automatically removed to keep the database clean.

## Tech Stack

*   **Framework:** [Streamlit](https://streamlit.io/)
*   **Language:** Python
*   **AI Word Generation:** [Groq API](https://groq.com/) (Llama 3 8B)
*   **Database:** SQLite

## Getting Started

### Prerequisites

*   Python 3.8+
*   A Groq API Key. You can get one for free at [groq.com](https://console.groq.com/keys).

### Local Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/rabbiachaudhary/imposter.git
    cd imposter
    ```

2.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your Groq API key:**
    Create a file at `.streamlit/secrets.toml` and add your API key:
    ```toml
    # .streamlit/secrets.toml
    GROQ_API_KEY = "YOUR_API_KEY_HERE"
    ```

4.  **Run the application:**
    ```bash
    streamlit run app.py
    ```
    The application will be available at `http://localhost:8501`.

### Running with GitHub Codespaces or Dev Containers

This repository is configured to run out-of-the-box with GitHub Codespaces or any Dev Container-compatible editor (like VS Code).

1.  Open the repository in a new Codespace.
2.  The environment will automatically build, install all dependencies, and start the application.
3.  Before the app can fully function, create the `.streamlit/secrets.toml` file as described in the local installation steps to add your Groq API key.
4.  The application will be forwarded to port `8501` and a preview will open automatically.
