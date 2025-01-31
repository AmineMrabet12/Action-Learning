"""
Streamlit Frontend for Text-to-Music Generator
==============================================

This module provides the frontend for a web application that allows users to generate music from text descriptions. 
It includes features like user authentication, token management, playlist creation, story posting, and profile management. 
The frontend is built using **Streamlit**, and it communicates with a **FastAPI** backend for data processing and storage.

Modules and Functions
---------------------
"""

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

st.set_page_config(initial_sidebar_state="collapsed")

API_URL = "http://localhost:8000"


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
    """,
    unsafe_allow_html=True
)
st.image("logo/logo_transparent.png", use_container_width=True)

# Display the logo



def translate_text(input_text: str, target_language: str = "en"):
    """
    Translate text to the specified target language.

    :param input_text: The text to translate.
    :param target_language: The target language code (default is "en" for English).
    :return: Translated text or an error message if translation fails.
    """
    try:
        translator = Translator()
        # Detect the language and translate the text
        translation = translator.translate(input_text, dest=target_language)
        return translation.text
    except Exception as e:
        return f"Translation failed: {e}"

# Pages
def show_home():
    """
    Display the home page for generating music from text descriptions.

    Features:
    - Input text description.
    - Translate non-English text to English.
    - Select music duration and song name.
    - Generate music using the backend API.
    """
    st.title("Text to Music Generator")
    st.markdown("**Enter a text description to generate music. If the input is in another language, it will be translated to English.**")

    # Fetch the user's token balance
    token_response = requests.get(f"{API_URL}/tokens/{st.session_state.user_id}")
    if token_response.status_code == 200:
        token_balance = token_response.json()["tokens"]
        st.info(f"**Your current token balance:** {token_balance} tokens")
    else:
        st.error("Failed to fetch token balance. Please try again later.")
        return

    model_options = ["musicgen-small", "musicgen-medium", "musicgen-large"]  # Replace with actual model names
    selected_model = st.selectbox("Choose a model for song generation:", model_options)

    if selected_model != "musicgen-small":
        st.warning("**Note:** Higher models costs more **Tokens** and takes longer **Time** to generate music")

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

        # Check if the user has enough tokens
        if token_balance < 10:
            st.error("You don't have enough tokens to generate a song. Please purchase more tokens.")
            return

        # Call the API to generate music
        with st.spinner("Generating..."):
            response = requests.post(f"{API_URL}/generate", json={
                "selected_model": selected_model,
                "description": translated_text,
                "duration": time_slider,
                "song_name": song_name
            }, params={"user_id": st.session_state.user_id})

        if response.status_code == 200:
            audio_path = response.json()["audio_path"]
            st.audio(audio_path)
            st.success("Song generated successfully! 10 tokens have been deducted.")

            # Update the token balance display
            token_balance -= 10
            st.write(f"**Remaining tokens:** {token_balance}")
        else:
            st.error(response.json()["detail"])

def generate_shareable_song_link(song_id):
    """
    Generate a shareable link for a song.

    :param song_id: The ID of the song.
    :return: A shareable link for the song.
    """
    base_url = "https://yourapp.com/song"
    unique_id = str(uuid.uuid4())
    return f"{base_url}/{song_id}/{unique_id}"

def create_share_button(platform, link, text):
    """
    Create a styled social sharing button.

    :param platform: The social media platform (e.g., "Twitter", "Facebook", "WhatsApp").
    :param link: The URL to share.
    :param text: The text to include in the share message.
    """
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


def show_login():
    """
    Display the login page for user authentication.
    """
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1, 1])

    with col1:
        login_button = st.button("Login", key="login_button", use_container_width=True)

    with col2:
        register_button = st.button("Register", key="register_button", use_container_width=True)

    if login_button:
        response = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
        if response.status_code == 200:
            user_data = response.json()

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
    """
    Log out the user and reset session state.
    """
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_id = None
    st.session_state.current_page = "home"
    st.success("Logged out successfully! App will refresh automatically")
    st.rerun()

def show_register():
    """
    Display the registration page for new users.
    """
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
    """
    Display the stories page for posting and viewing stories.
    """
    st.title("Your Stories")


    response = requests.get(f"{API_URL}/stories", params={"user_id": st.session_state.user_id})
    
    if response.status_code == 200:
        stories = response.json()

        if not stories:
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
    """
    Display a form for posting a new story.
    """
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
                st.session_state.current_page = "stories"
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


# def show_profile():
#     """Show the user's profile and allow editing."""
#     st.title("User Profile")

#     # Fetch profile details if not already loaded
#     if not st.session_state.user_profile:
#         get_user_profile()

#     # Profile Picture
#     st.subheader("Profile Picture")
#     uploaded_image = st.file_uploader("Upload a New Profile Picture", type=["jpg", "jpeg", "png"])

#     if uploaded_image:
#         image = Image.open(uploaded_image)
#         st.image(image, caption="New Profile Picture", use_container_width=True)
#         st.session_state.user_profile["profile_picture"] = image  # Store the image directly

#     # Display Existing Profile Picture if Available
#     if "profile_picture" in st.session_state.user_profile and st.session_state.user_profile["profile_picture"]:
#         profile_picture = st.session_state.user_profile["profile_picture"]
#         st.image(profile_picture, caption="Current Profile Picture", use_container_width=True)

#     # User Details Form
#     st.subheader("Edit Profile Details")
#     st.session_state.user_profile["first_name"] = st.text_input("First Name", st.session_state.user_profile.get("first_name", ""))
#     st.session_state.user_profile["last_name"] = st.text_input("Last Name", st.session_state.user_profile.get("last_name", ""))
#     st.session_state.user_profile["email"] = st.text_input("Email", st.session_state.user_profile.get("email", ""))
#     st.session_state.user_profile["dob"] = st.date_input("Date of Birth", st.session_state.user_profile.get("dob", None))
#     st.session_state.user_profile["address"] = st.text_area("Address", st.session_state.user_profile.get("address", ""))

#     # Save Button
#     if st.button("Save Profile"):
#         userID = st.session_state.user_id
#         update_user_profile(userID)

def show_profile_preview():
    st.subheader("Profile Preview")

    # Display profile details
    profile = st.session_state.user_profile
    if profile:
        st.write(f"**First Name:** {profile.get('first_name', 'N/A')}")
        st.write(f"**Last Name:** {profile.get('last_name', 'N/A')}")
        st.write(f"**Email:** {profile.get('email', 'N/A')}")
        st.write(f"**Date of Birth:** {profile.get('dob', 'N/A')}")
        st.write(f"**Address:** {profile.get('address', 'N/A')}")

        # Display profile picture if available
        if profile.get("profile_picture"):
            st.image(profile["profile_picture"], caption="Profile Picture", use_container_width=True)
        else:
            st.write("**Profile Picture:** No image uploaded.")
    else:
        st.error("No profile data found.")

def show_profile_modify():
    st.subheader("Modify Profile")

    # Fetch profile details if not already loaded
    if not st.session_state.user_profile:
        get_user_profile()

    # Display form for modifying profile
    profile = st.session_state.user_profile
    if profile:
        first_name = st.text_input("First Name", profile.get("first_name", ""))
        last_name = st.text_input("Last Name", profile.get("last_name", ""))
        email = st.text_input("Email", profile.get("email", ""))
        dob = st.date_input("Date of Birth", value=profile.get("dob", None))
        address = st.text_area("Address", profile.get("address", ""))
        uploaded_image = st.file_uploader("Upload a New Profile Picture", type=["jpg", "jpeg", "png"])

        # Save changes
        if st.button("Save Changes"):
            # Update the profile data
            updated_profile = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "dob": dob,
                "address": address,
                "profile_picture": uploaded_image if uploaded_image else profile.get("profile_picture")
            }

            # Send the updated profile to the backend
            response = update_user_profile(updated_profile)
            if response:
                st.success("Profile updated successfully!")
                st.session_state.profile_mode = "preview"  # Switch back to preview mode
                st.rerun()
            else:
                st.error("Failed to update profile. Please try again.")
    else:
        st.error("No profile data found.")

def show_profile():
    st.title("User Profile")

    # Add two buttons: "Preview" and "Modify"
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Preview Profile", use_container_width=True):
            st.session_state.profile_mode = "preview"
    with col2:
        if st.button("Modify Profile", use_container_width=True):
            st.session_state.profile_mode = "modify"

    # Initialize profile_mode in session state if it doesn't exist
    if "profile_mode" not in st.session_state:
        st.session_state.profile_mode = "preview"  # Default to preview mode

    # Fetch profile details if not already loaded
    if not st.session_state.user_profile:
        get_user_profile()

    # Display the appropriate section based on the selected mode
    if st.session_state.profile_mode == "preview":
        show_profile_preview()
    elif st.session_state.profile_mode == "modify":
        show_profile_modify()


def update_user_profile(updated_profile):
    """Update user profile by sending the data to the backend."""
    try:
        # Prepare the data for the request
        profile_data = {
            "first_name": updated_profile.get("first_name"),
            "last_name": updated_profile.get("last_name"),
            "email": updated_profile.get("email"),
            "dob": updated_profile.get("dob").isoformat() if updated_profile.get("dob") else None,
            "address": updated_profile.get("address")
        }

        # Handle the profile picture upload
        if "profile_picture" in updated_profile and updated_profile["profile_picture"]:
            # If an image was uploaded, send it as a file
            files = {"profile_picture": ("profile_picture.png", updated_profile["profile_picture"], "image/png")}
            response = requests.put(f"{API_URL}/profile/{st.session_state.user_id}", files=files, data=profile_data)
        else:
            # If no image was uploaded, send only the profile data
            response = requests.put(f"{API_URL}/profile/{st.session_state.user_id}", json=profile_data)

        if response.status_code == 200:
            return True
        else:
            st.error(f"Failed to update profile: {response.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return False


def get_user_profile():
    """Fetch user profile from the backend API."""
    response = requests.get(f"{API_URL}/profile/{st.session_state.user_id}")
    if response.status_code == 200:
        st.session_state.user_profile = response.json()
    else:
        st.error("Failed to load profile.")
    

# Function to show the search page
def show_search_page():
    st.title("Search for Users")

    # Search bar
    search_query = st.text_input("Search profiles (First Name, Last Name, Email):")

    if search_query:
        # Fetch user profiles from the database (simulated)
        profiles = [
            {"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com", "user_id": 1},
            {"first_name": "Jane", "last_name": "Smith", "email": "jane.smith@example.com", "user_id": 2},
            {"first_name": "Mike", "last_name": "Johnson", "email": "mike.johnson@example.com", "user_id": 3},
            {"first_name": "Emily", "last_name": "Davis", "email": "emily.davis@example.com", "user_id": 4},
            {"first_name": "Daniel", "last_name": "Martinez", "email": "daniel.martinez@example.com", "user_id": 5},
            {"first_name": "Olivia", "last_name": "Wilson", "email": "olivia.wilson@example.com", "user_id": 6},
            {"first_name": "William", "last_name": "Anderson", "email": "william.anderson@example.com", "user_id": 7},
            {"first_name": "Sophia", "last_name": "Brown", "email": "sophia.brown@example.com", "user_id": 8},
            {"first_name": "James", "last_name": "Miller", "email": "james.miller@example.com", "user_id": 9},
            {"first_name": "Charlotte", "last_name": "Taylor", "email": "charlotte.taylor@example.com", "user_id": 10},
            {"first_name": "Liam", "last_name": "Garcia", "email": "liam.garcia@example.com", "user_id": 11},
            {"first_name": "Isabella", "last_name": "Rodriguez", "email": "isabella.rodriguez@example.com", "user_id": 12},
            {"first_name": "Ethan", "last_name": "Harris", "email": "ethan.harris@example.com", "user_id": 13},
            {"first_name": "Mia", "last_name": "Clark", "email": "mia.clark@example.com", "user_id": 14},
            {"first_name": "Benjamin", "last_name": "Lewis", "email": "benjamin.lewis@example.com", "user_id": 15}
        ]

        # Filter profiles based on search query
        filtered_profiles = [
            profile for profile in profiles if search_query.lower() in f"{profile['first_name']} {profile['last_name']} {profile['email']}".lower()
        ]

        if filtered_profiles:
            st.write(f"Found {len(filtered_profiles)} result(s):")
            for profile in filtered_profiles:
                st.button(f"{profile['first_name']} {profile['last_name']} - {profile['email']}", use_container_width=True)
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

def show_tokens():
    st.title("Token Management")

    # Fetch the user's current token balance
    response = requests.get(f"{API_URL}/tokens/{st.session_state.user_id}")
    if response.status_code == 200:
        token_balance = response.json()["tokens"]
        st.info(f"Your current token balance: {token_balance} tokens")
    else:
        st.error("Failed to fetch token balance.")

    # Token purchase section
    st.subheader("Purchase Tokens")
    token_amount = st.number_input("Enter the number of tokens you want to purchase", min_value=1, value=10)

    if st.button("Purchase Tokens"):
        # Send user_id and amount as query parameters
        response = requests.post(
            f"{API_URL}/purchase_tokens",
            params={"user_id": st.session_state.user_id, "amount": token_amount}  # Use params for query parameters
        )
        
        # Check if the response is valid JSON
        try:
            if response.status_code == 200:
                st.success(f"Successfully purchased {token_amount} tokens!")
                sleep(2)
                st.session_state.current_page = "home"  # Refresh the page
                st.rerun()
            else:
                st.error(f"Failed to purchase tokens: {response.json().get('detail', 'Unknown error')}")
        except ValueError:  # Handle JSON decode error
            st.error("Failed to process the response from the server. Please try again.")

# Main
if __name__ == "__main__":
    # Check if the user is logged in
    if st.session_state.logged_in:
        st.sidebar.button("Profile", on_click=lambda: st.session_state.update({"current_page": "profile"}), use_container_width=True)
        st.sidebar.button("Home", on_click=lambda: st.session_state.update({"current_page": "home"}), use_container_width=True)
        st.sidebar.button("Playlist", on_click=lambda: st.session_state.update({"current_page": "playlist"}), use_container_width=True)
        st.sidebar.button("Stories", on_click=lambda: st.session_state.update({"current_page": "stories"}), use_container_width=True)
        st.sidebar.button("Search", on_click=lambda: st.session_state.update({"current_page": "search"}), use_container_width=True)
        st.sidebar.button("Tokens", on_click=lambda: st.session_state.update({"current_page": "tokens"}), use_container_width=True)  # New Tokens button
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
        elif st.session_state.current_page == "tokens":  # Handle the tokens page
            show_tokens()

    else:
        # If not logged in, show login or register pages
        if st.session_state.register_mode:
            show_register()
        else:
            show_login()

