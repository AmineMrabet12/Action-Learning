import streamlit as st
from music_generator import *  # Import the necessary functions from music_generator.py
from auth import save_song_to_db, get_user_playlist, login, register, logout  # Import necessary functions from auth.py

# Initialize session state attributes if not already initialized
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "register_mode" not in st.session_state:
    st.session_state.register_mode = False  # Initially, not in register mode

def main():
    st.title("Text to Music Generator")

    with st.expander("See explanation"):
        st.write("Music Generator app built using Meta's Audiocraft library. We are using Music Gen Small model.")

    # Get the description from the user
    text_area = st.text_area("Enter your description.......")
    time_slider = st.slider("Select time duration (In Seconds)", 0, 20, 10)
    
    # User input for song name
    song_name = st.text_input("Enter song name:")
    
    if text_area and time_slider and song_name:
        st.json({
            'Your Description': text_area,
            'Selected Time Duration (in Seconds)': time_slider,
            'Song Name': song_name
        })

        st.subheader("Generated Music")
        music_tensors = generate_music_tensors(text_area, time_slider)
        print("Music Tensors: ", music_tensors)
        save_audio(music_tensors, song_name, text_area)  # Save the song with the given name
        
        audio_filepath = f'audio_output/{song_name}.wav'
        audio_file = open(audio_filepath, 'rb')
        audio_bytes = audio_file.read()
        st.audio(audio_bytes)
        st.markdown(get_binary_file_downloader_html(audio_filepath, 'Audio'), unsafe_allow_html=True)

# Sidebar layout for logged-in users
def show_sidebar():
    with st.sidebar:
        # Logout button
        if st.button("Logout"):
            logout()  # This will log the user out and return to the login page

        # Home button to go back to the music generator page
        if st.button("Home"):
            st.session_state.logged_in = True  # Keep user logged in
            st.session_state.register_mode = False  # Ensure the register mode is off
            # st.experimental_rerun()  # This will rerun the app and show the music generator page

        # Playlist section
        st.subheader("Playlist")
        playlist_button = st.button("View Playlist")
        
        return playlist_button  # Return button to the main function for controlling visibility

# Playlist inside the main page
def show_playlist():
    # Get the user's playlist from the database
    songs = get_user_playlist(st.session_state.user_id)
    
    if songs:
        for song in songs:
            song_id, song_name, description, audio_data = song
            
            # Display the song name and description
            st.write(f"**{song_name}** - {description}")
            
            # Use a unique key for each play button to prevent rerun
            play_button = st.button(f"Play {song_name}", key=f"play_{song_id}")
            
            if play_button:
                # Stream the audio data directly
                st.audio(audio_data, format="audio/wav")
    else:
        st.write("You have no songs in your playlist yet.")

# Login form
def show_login_form():
    st.title("Welcome to the Login Page")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns([7, 1])
    
    with col1:
        login_action = st.button("Login", key="login_action")

    with col2:
        register_button = st.button("Register", key="register_button")

    if login_action:
        user = login(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_id = user[0]  # Assuming the user ID is the first column in the users table
            st.success("Successfully logged in!")
            # st.experimental_rerun()  # This will rerun the app and show the main page
        else:
            st.error("Invalid username or password.")
        
    if register_button:
        st.session_state.register_mode = True  # Switch to register mode

# Register form
def show_register_form():
    st.title("Register Page")

    new_username = st.text_input("New Username")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    col1, col2 = st.columns([5, 1])

    with col1:
        register_action = st.button("Register", key="register_action")

    with col2:
        back_to_login_button = st.button("Back to Login", key="back_to_login_button")

    if register_action:
        if new_password != confirm_password:
            st.error("Passwords do not match.")
        else:
            if register(new_username, new_password):
                st.success("Registration successful! You can now login.")
                st.session_state.register_mode = False
            else:
                st.error("Username already exists.")
        
    if back_to_login_button:
        st.session_state.register_mode = False  # Switch back to login mode

# Main app logic
if __name__ == "__main__":
    if st.session_state.logged_in:
        # Show the sidebar and check if the user clicked the "View Playlist" button
        playlist_button_clicked = show_sidebar()  # Check if the playlist button was clicked

        if playlist_button_clicked:
            # If playlist button is clicked, show the playlist inside the main page
            show_playlist()
        else:
            # Otherwise, show the music generator page
            main()
    else:
        if not st.session_state.register_mode:
            show_login_form()  # Display the login form
        else:
            show_register_form()  # Display the register form
