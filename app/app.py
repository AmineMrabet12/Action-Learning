import streamlit as st
import requests
import base64
import uuid
import urllib.parse
from googletrans import Translator
import pyperclip
from diffusers import DiffusionPipeline
from time import sleep
from io import BytesIO
from PIL import Image

API_URL = "http://localhost:8000"

# Initialize session state
# Initialize session state for user profile
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {}

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


#########################################################################
########################### Show User Profile ###########################
#########################################################################

def get_user_profile():
    """Fetch user profile from the backend API."""
    response = requests.get(f"{API_URL}/profile", params={"user_id": st.session_state.user_id})
    if response.status_code == 200:
        st.session_state.user_profile = response.json()
    else:
        st.error("Failed to load profile.")


def update_user_profile(user_id):
    """Update user profile by sending the data to the backend."""
    try:
        user_profile = st.session_state.user_profile
        if user_profile.get("dob"):
            user_profile["dob"] = user_profile["dob"].isoformat()  # Convert to ISO string

        # Prepare the data for the request
        profile_data = {
            "first_name": user_profile.get("first_name"),
            "last_name": user_profile.get("last_name"),
            "dob": user_profile.get("dob"),
            "email": user_profile.get("email"),
            "address": user_profile.get("address")
        }

        # Handle the profile picture upload
        if "profile_picture" in user_profile:
            # Directly send the file, no need for base64 encoding
            profile_picture = user_profile["profile_picture"]
            if isinstance(profile_picture, Image.Image):  # If image was uploaded
                profile_picture = profile_picture.convert("RGB")
                # Save the image to a buffer
                buffered = BytesIO()
                profile_picture.save(buffered, format="PNG")
                buffered.seek(0)
                files = {"profile_picture": ("profile_picture.png", buffered, "image/png")}
                response = requests.put(f"{API_URL}/profile/{user_id}", files=files, data=profile_data)
            else:
                # If there is no image, just send the user profile data
                response = requests.put(f"{API_URL}/profile/{user_id}", json=profile_data)

        if response.status_code == 200:
            st.success("Profile updated successfully.")
        else:
            st.error(f"Failed to update profile: {response.json()['detail']}")
    except Exception as e:
        st.error(f"An error occurred: {e}")


def show_profile():
    """Show the user's profile and allow editing."""
    st.title("User Profile")

    # Fetch profile details if not already loaded
    if not st.session_state.user_profile:
        get_user_profile()

    # Profile Picture
    st.subheader("Profile Picture")
    uploaded_image = st.file_uploader("Upload a New Profile Picture", type=["jpg", "jpeg", "png"])

    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption="New Profile Picture", use_container_width=True)
        st.session_state.user_profile["profile_picture"] = image  # Store the image directly

    # Display Existing Profile Picture if Available
    if "profile_picture" in st.session_state.user_profile and st.session_state.user_profile["profile_picture"]:
        profile_picture = st.session_state.user_profile["profile_picture"]
        st.image(profile_picture, caption="Current Profile Picture", use_container_width=True)

    # User Details Form
    st.subheader("Edit Profile Details")
    st.session_state.user_profile["first_name"] = st.text_input("First Name", st.session_state.user_profile.get("first_name", ""))
    st.session_state.user_profile["last_name"] = st.text_input("Last Name", st.session_state.user_profile.get("last_name", ""))
    st.session_state.user_profile["email"] = st.text_input("Email", st.session_state.user_profile.get("email", ""))
    st.session_state.user_profile["dob"] = st.date_input("Date of Birth", st.session_state.user_profile.get("dob", None))
    st.session_state.user_profile["address"] = st.text_area("Address", st.session_state.user_profile.get("address", ""))

    # Save Button
    if st.button("Save Profile"):
        userID = st.session_state.user_id
        update_user_profile(userID)


def get_user_profiles():
    """Fetch user profiles from the database via API."""
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

def initialize_model():
    if "model" not in st.session_state:
        try:
            # Load the AnimateDiff model pipeline
            pipe = DiffusionPipeline.from_pretrained("emilianJR/epiCRealism")#.to(device)
            st.session_state.model = pipe
            return pipe
        except Exception as e:
            st.error(f"Model initialization failed: {str(e)}")
            return None
    return st.session_state.model

def show_animation_generator():
    st.subheader("Generate Animation")
    prompt = st.text_input("Enter animation prompt")
    
    if prompt and st.button("Generate Animation"):
        try:
            # Initialize model
            pipe = initialize_model()

            with st.spinner("Generating animation..."):
                # Generate the image or animation
                output = pipe(prompt)
                image = output.images[0]

                # Save and display the image
                output_path = "gen_img/generated_image.png"
                image.save(output_path)
                st.success("Animation generated successfully!")
                st.image(output_path)

        except Exception as e:
            st.error(f"Error generating animation: {str(e)}")

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
            # show_stories()  # Show the stories page
            show_animation_generator()
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

