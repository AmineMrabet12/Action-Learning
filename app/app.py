import streamlit as st
# import streamlit.components.v1 as components
import requests
import base64
import uuid
import urllib.parse
from googletrans import Translator
import pyperclip
from time import sleep

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
        with st.spinner("Generating..."):
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

def generate_shareable_song_link(song_id):
    """Generate a shareable link for a song"""
    base_url = "https://yourapp.com/song"
    unique_id = str(uuid.uuid4())
    return f"{base_url}/{song_id}/{unique_id}"

def create_share_button(platform, link, text):
    """Create styled social sharing buttons"""
    platforms = {
        "Twitter": f"https://twitter.com/intent/tweet?text={urllib.parse.quote(f'Check this out: {text}!')}+{urllib.parse.quote(link)}",
        "Facebook": f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(link)}",
        "WhatsApp": f"https://api.whatsapp.com/send?text={urllib.parse.quote(f'Check this out: {text}! {link}')}"
    }

    st.markdown(
        f"""
        <a href="{platforms[platform]}" target="_blank" style="text-decoration:none;">
        <button style="background-color:#4CAF50; color:white; border:none; 
                padding:10px 16px; border-radius:8px; margin-right:8px; cursor:pointer; font-size:14px; display: flex; justify-content: space-between;">
            Share on {platform}
        </button>
        </a>
        """,
        unsafe_allow_html=True,
    )


def show_playlist():
    """Display user playlist with play, delete, and share options"""
    st.title("🎵 Your Playlist")
    
    response = requests.get(f"{API_URL}/playlist", params={"user_id": st.session_state.user_id})
    if response.status_code == 200:
        songs = response.json()

        if not songs:
            st.info("You don't have a playlist. Generate songs to see your list.")
            return

        for song in songs:
            st.write(f"**{song['song_name']}** - {song['description']}")
            song_url = generate_shareable_song_link(song['id'])

            col1, col2, col3 = st.columns([1, 1, 1])

            with col1:
                play_butt = st.button(f"▶️ Play {song['song_name']}", key=f"play_{song['id']}", use_container_width=True)

            if play_butt:
                song_response = requests.get(f"{API_URL}/song/{song['id']}")
                if song_response.status_code == 200:
                    song_data = song_response.json()
                    # st.audio(song_data['audio_url'])
                    audio_data = base64.b64decode(song_data['audio_data'])
                    st.audio(audio_data)

            with col2:
                del_butt = st.button(f"❌ Delete {song['song_name']}", key=f"delete_{song['id']}", use_container_width=True)

            if del_butt:
                delete_response = requests.delete(f"{API_URL}/song/{song['id']}")
                if delete_response.status_code == 200:
                    st.success(f"✅ '{song['song_name']}' deleted successfully! Refreshing...")
                    sleep(2)
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete '{song['song_name']}'.")

            with col3:
                share_butt = st.button(f"🔗 Share {song['song_name']}", key=f"share_{song['id']}", use_container_width=True)

            if share_butt:
                st.markdown("### 📢 Share this song on Social Media:")
                col1, col2, col3 = st.columns(3, gap="large")
                with col1:
                    create_share_button("Twitter", song_url, song['song_name'])
                with col2:
                    create_share_button("Facebook", song_url, song['song_name'])
                with col3:
                    create_share_button("WhatsApp", song_url, song['song_name'])

                # Copy Link Button
                st.markdown("### 🔗 Copy Shareable Link")
                # col1, col2 = st.columns([4, 1])
                # with col1:
                st.text_input(label="", value=song_url, key=f"link_{song['id']}")
                # with col2:
                    # Create a button that will copy the link to clipboard
                if st.button("Copy Link", key=f"copy_{song['id']}"):
                    # Using `pyperclip` to copy the song URL to clipboard
                    st.success("Link copied to clipboard!")
                    pyperclip.copy(song_url)

                # else:
                #     st.error("❌ Failed to fetch playlist.")

def show_login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1, 1])  # Create two columns

    with col1:
        login_button = st.button("Login", key="login_button", use_container_width=True)

    with col2:
        register_button = st.button("Register", key="register_button", use_container_width=True)

    if login_button:
        response = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
        if response.status_code == 200:
            user_data = response.json()
            # Store login information in session state
            st.session_state.logged_in = True
            st.session_state.username = user_data["username"]
            st.session_state.user_id = user_data["user_id"]
            st.success("Successfully logged in! App will refresh automatically")
            st.session_state.current_page = "home"
            sleep(2)
            st.rerun()
            
        else:
            st.error("Invalid credentials")

    if register_button:
        st.session_state.register_mode = True
        st.rerun()


def show_logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_id = None
    st.session_state.current_page = "home"
    st.success("Logged out successfully! App will refresh automatically")
    st.rerun()


def show_register():
    st.title("Register")
    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    col1, col2 = st.columns([1, 1])  # Create two columns

    with col1:
        register_submit_button = st.button("Register", use_container_width=True)

    with col2:
        back_to_login_button = st.button("Back to Login", use_container_width=True)

    if register_submit_button:
        # Validation: Check for empty fields
        if not username.strip():
            st.error("Username cannot be empty.")
            return
        if not password.strip():
            st.error("Password cannot be empty.")
            return
        if password != confirm_password:
            st.error("Passwords do not match.")
            return
    
    if register_submit_button:
        response = requests.post(f"{API_URL}/register", json={"username": username, "password": password, "confirm_password": confirm_password})
        if response.status_code == 200:
            st.success("Registration successful! Please login. App will refresh automatically")
            st.session_state.register_mode = False
            sleep(2)
            st.rerun()
        else:
            st.error(response.json()["detail"])

    if back_to_login_button:
        st.session_state.register_mode = False
        st.rerun()

def show_stories():
    st.title("Your Stories")

    # Get existing stories
    response = requests.get(f"{API_URL}/stories", params={"user_id": st.session_state.user_id})
    
    if response.status_code == 200:
        stories = response.json()

        if not stories:  # No active stories available
            st.info("You don't have any active stories.")
        
        # Display the existing stories
        for story in stories:
            st.write(f"**Story ID: {story['id']}**")
            st.write(f"**Content**: {story['content']}")
            st.write(f"**Expires At**: {story['expires_at']}")

    else:
        st.error("Failed to fetch stories.")
    
    # Option to post a new story
    if st.button("Post New Story"):
        post_story_form()

def post_story_form():
    st.title("Post a Story")
    story_content = st.text_area("Enter your story content (text, image URL, or video URL)")
    
    if st.button("Post Story"):
        if story_content:
            response = requests.post(f"{API_URL}/post_story", json={
                "user_id": st.session_state.user_id,
                "content": story_content
            })

            if response.status_code == 200:
                st.success("Story posted successfully!")
                st.session_state.current_page = "stories"  # Navigate back to stories page
                sleep(2)
                st.rerun()
            else:
                st.error("Failed to post story.")
        else:
            st.error("Please enter some content for the story.")

def show_profile():
    st.title("Profile")
    
    # Allow user to upload a profile picture
    uploaded_image = st.file_uploader("Upload Profile Picture", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        st.image(uploaded_image, caption="Profile Picture", use_container_width=True)

    # Input fields for user details
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    dob = st.date_input("Date of Birth")
    email = st.text_input("Email")
    address = st.text_area("Address")

    # Display the input data
    if st.button("Save Profile"):
        if all([first_name, last_name, dob, email, address]):
            st.success("Profile saved successfully!")
            # In a real app, you could save these details to a database or file
        else:
            st.error("Please fill in all fields.")

def get_user_profiles():
    return [
        {"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com", "user_id": 1},
        {"first_name": "Jane", "last_name": "Smith", "email": "jane.smith@example.com", "user_id": 2},
        {"first_name": "Mike", "last_name": "Johnson", "email": "mike.johnson@example.com", "user_id": 3},
    ]


# Function to show the search page
def show_search_page():
    st.title("Search for Users")

    # Search bar
    search_query = st.text_input("Search profiles (First Name, Last Name, Email):")

    if search_query:
        # Fetch user profiles from the database (simulated)
        profiles = get_user_profiles()

        # Filter profiles based on search query
        filtered_profiles = [
            profile for profile in profiles if search_query.lower() in f"{profile['first_name']} {profile['last_name']} {profile['email']}".lower()
        ]

        if filtered_profiles:
            st.write(f"Found {len(filtered_profiles)} result(s):")
            for profile in filtered_profiles:
                st.write(f"{profile['first_name']} {profile['last_name']} - {profile['email']}")
        else:
            st.write("No results found.")


# Main
if __name__ == "__main__":
    # Check if the user is logged in
    if st.session_state.logged_in:
        # If logged in, show the sidebar options
        st.sidebar.button("Profile", on_click=lambda: st.session_state.update({"current_page": "profile"}), use_container_width=True)
        st.sidebar.button("Home", on_click=lambda: st.session_state.update({"current_page": "home"}), use_container_width=True)
        st.sidebar.button("Playlist", on_click=lambda: st.session_state.update({"current_page": "playlist"}), use_container_width=True)
        st.sidebar.button("Stories", on_click=lambda: st.session_state.update({"current_page": "stories"}), use_container_width=True)
        st.sidebar.button("Search", on_click=lambda: st.session_state.update({"current_page": "search"}), use_container_width=True)
        st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logged_in": False, "username": "", "user_id": None}), use_container_width=True)

        # Show the page based on the current_page value
        if st.session_state.current_page == "home":
            show_home()
        elif st.session_state.current_page == "playlist":
            show_playlist()
        elif st.session_state.current_page == "stories":
            show_stories()  # Show the stories page
        elif st.session_state.current_page == "profile":
            show_profile()
        elif st.session_state.current_page == "search":
            show_search_page()

    else:
        # If not logged in, show login or register pages
        if st.session_state.register_mode:
            show_register()
        else:
            show_login()

