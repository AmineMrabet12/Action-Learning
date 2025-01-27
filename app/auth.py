import streamlit as st
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection (adjust as needed)
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

# Save song details in the database, with audio as binary data
def save_song_to_db(user_id, song_name, description, audio_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert the song details into the songs table, including the description and audio data
    cursor.execute(
        "INSERT INTO songs (user_id, song_name, description, audio_data) VALUES (%s, %s, %s, %s)", 
        (user_id, song_name, description, audio_data)
    )
    conn.commit()
    conn.close()

# Get user's playlist from the database
def get_user_playlist(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the list of songs for the current user, including the description
    cursor.execute("SELECT id, song_name, description, audio_data FROM songs WHERE user_id = %s", (user_id,))
    songs = cursor.fetchall()
    conn.close()
    
    return songs

# Login function
def login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

# Register function
def register(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the username already exists
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return False  # Username already exists
    
    # Insert the new user into the database
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
    conn.commit()
    conn.close()
    return True

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "register_mode" not in st.session_state:
    st.session_state.register_mode = False  # Initially, not in register mode

# Logout function
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_id = None
    st.session_state.register_mode = False  # Reset register mode on logout
    st.experimental_rerun()  # This will rerun the app and show the login page
