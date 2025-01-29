import streamlit as st
import requests
import base64
from googletrans import Translator

API_URL = "http://localhost:8000"

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "register_mode" not in st.session_state:
    st.session_state.register_mode = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"


st.markdown(
    """
    <style>
    .st-emotion-cache-6qob1r.e1dbuyne8 {  /* Sidebar style */
        display: flex;
        flex-direction: column;
        justify-content: center;
        height: 100%;
        padding-top: 50px;  /* Optional, add space from top */
    }
    .stElementContainer.element-container.st-emotion-cache-k3ze7c.eiemyj1 {  /* Style for each button in sidebar */
        width: 100%;
        text-align: center;
        font-size: 18px;
    }
    .st-emotion-cache-zaw6nw.e1obcldf2 {
        width: 100%;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True
)




def translate_text(input_text: str, target_language: str = "en"):
    try:
        translator = Translator()
        # Detect the language and translate the text
        translation = translator.translate(input_text, dest=target_language)
        return translation.text
    except Exception as e:
        return f"Translation failed: {e}"

# Pages
def show_home():
    st.title("Text to Music Generator")
    st.markdown("**Enter a text description to generate music. If the input is in another language, it will be translated to English.**")

    # User input for text description
    text_area = st.text_area("Enter your description")
    translate_option = st.checkbox("Translate description to English (if not in English)")
    translated_text = text_area  # Default to user input

    # Translate the text if the user opts in
    if translate_option and text_area:
        with st.spinner("Translating..."):
            try:
                translated_text = translate_text(text_area, target_language="en")
                st.success(f"Translated Text: {translated_text}")
            except Exception as e:
                st.error(f"Translation failed: {e}")

    # Select the duration of music and song name
    time_slider = st.slider("Select time duration (In Seconds)", 0, 20, 10)
    song_name = st.text_input("Enter song name:")

    # Generate music
    if st.button("Generate Music"):
        if not translated_text:
            st.error("Please enter a description before generating music!")
            return

        # Call the API to generate music
        response = requests.post(f"{API_URL}/generate", json={
            "description": translated_text,
            "duration": time_slider,
            "song_name": song_name
        }, params={"user_id": st.session_state.user_id})

        if response.status_code == 200:
            audio_path = response.json()["audio_path"]
            st.audio(audio_path)
        else:
            st.error(response.json()["detail"])

def show_playlist():
    st.title("Your Playlist")
    response = requests.get(f"{API_URL}/playlist", params={"user_id": st.session_state.user_id})
    if response.status_code == 200:
        songs = response.json()
        for song in songs:
            st.write(f"**{song['song_name']}** - {song['description']}")
            if st.button(f"Play {song['song_name']}", key=song['id']):
                song_response = requests.get(f"{API_URL}/song/{song['id']}")
                if song_response.status_code == 200:
                    song_data = song_response.json()
                    audio_data = base64.b64decode(song_data['audio_data'])
                    st.audio(audio_data)
    else:
        st.error("Failed to fetch playlist")

def show_login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([7, 1])  # Create two columns

    with col1:
        login_button = st.button("Login", key="login_button")

    with col2:
        register_button = st.button("Register", key="register_button")

    if login_button:
        response = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
        if response.status_code == 200:
            user_data = response.json()
            st.session_state.logged_in = True
            st.session_state.username = user_data["username"]
            st.session_state.user_id = user_data["user_id"]
            st.success("Successfully logged in!")
        else:
            st.error("Invalid credentials")

    # with col2:
    #     register_button = st.button("Register", key="register_button")
    if register_button:
        st.session_state.register_mode = True

def show_register():
    st.title("Register")
    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    col1, col2 = st.columns([5, 1])  # Create two columns

    with col1:
        register_submit_button = st.button("Register")

    with col2:
        back_to_login_button = st.button("Back to Login")
    
    if register_submit_button:
        response = requests.post(f"{API_URL}/register", json={"username": username, "password": password, "confirm_password": confirm_password})
        if response.status_code == 200:
            st.success("Registration successful! Please login.")
            st.session_state.register_mode = False
        else:
            st.error(response.json()["detail"])

    if back_to_login_button:
        st.session_state.register_mode = False

# Main
if __name__ == "__main__":
    if st.session_state.logged_in:
        st.sidebar.button("Home", on_click=lambda: st.session_state.update({"current_page": "home"}))
        st.sidebar.button("Playlist", on_click=lambda: st.session_state.update({"current_page": "playlist"}))
        st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False, "username": "", "user_id": None}))

        if st.session_state.current_page == "home":
            show_home()
        elif st.session_state.current_page == "playlist":
            show_playlist()
    else:
        if st.session_state.register_mode:
            show_register()
        else:
            show_login()
