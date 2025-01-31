# Text-to-Music Generator with User Profiles and Token System

## Overview
This project is a web application that allows users to generate music from text descriptions. It includes features like user authentication, token management, playlist creation, story posting, and profile management. The application is built using **Streamlit** for the frontend and **FastAPI** for the backend.

---

## Features
1. **Text-to-Music Generation**:
   - Users can input a text description and generate music.
   - Supports translation of non-English text to English for better results.

2. **User Authentication**:
   - Users can register, log in, and log out.
   - New users receive **20 free tokens** upon registration.

3. **Token System**:
   - Generating a song costs **10 tokens**.
   - Users can purchase additional tokens.

4. **Playlist Management**:
   - Users can view, play, and delete their generated songs.
   - Songs can be shared via social media or direct links.

5. **Story Posting**:
   - Users can post stories (text, image, or video links).
   - Stories expire after **24 hours**.

6. **Profile Management**:
   - Users can view and update their profile information.
   - Supports profile picture uploads.

7. **Animation Generator**:
   - Users can generate animations from text prompts using a pre-trained model.

---

## Technologies Used
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **Deep Learning**: MusicGen (for music generation), DiffusionPipeline (for animation generation)
- **Other Libraries**:
  - `googletrans` for text translation
  - `requests` for API communication
  - `torchaudio` for audio processing
  - `PIL` for image handling

---

## Project Structure
```bash
├── README.md
├── action_learning.pem
├── app
│   ├── __pycache__
│   ├── app.py
│   ├── audio_output
│   ├── gen_img
│   ├── logo
│   └── main.py
├── code
│   ├── inference.py
│   ├── test.py
│   └── test2.py
├── data
├── models
│   ├── audio_features_padded.npy
│   ├── model.h5
│   └── text_embeddings.npy
├── notebooks
│   ├── Copy_of_download_musiccaps.ipynb
│   └── preprocess.ipynb
└── requirements.txt
```

---

## Setup Instructions

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Backend Setup

1. Install the required dependencies:

    ```bash
    cd Action-Learning
    pip install -r requirements.txt
    ```

1. Navigate to the `app` directory:
   ```bash
   cd app
   ```

3. Run the FastAPI
    ```bash
    fastapi run main.py
    ```

    The backend will be available at `http://localhost:8000`.

### Frontend Setup

```bash
streamlit run app.py
```

The frontend will be available at `http://localhost:8501`.

---
## Usage

### Home Page

- Enter a text description to generate music.
- Translate non-English text to English (optional).
- Select the duration of the music and provide a song name.
- Click Generate Music to create a song (costs 10 tokens). 

### Playlist

- View all generated songs.
- Play, delete, or share songs.

### Tokens

- Check your token balance.
- Purchase additional tokens.

### Stories

- Post stories (text, image, or video links).
- View active stories (expire after 24 hours).

### Profile

- View your profile information.
- Update your profile (first name, last name, email, address, profile picture).

### Animation Generator

- Enter a text prompt to generate an animation.

## API Endpoints (Backend)

| **HTTP Method** | **Endpoint**                     | **Description**                              |
|-----------------|----------------------------------|----------------------------------------------|
| `POST`          | `/register`                     | Register a new user.                         |
| `POST`          | `/login`                        | Log in an existing user.                     |
| `POST`          | `/generate`                     | Generate music from a text description.      |
| `GET`           | `/playlist`                     | Get the user's playlist.                     |
| `GET`           | `/song/{song_id}`               | Get a specific song.                         |
| `DELETE`        | `/song/{song_id}`               | Delete a specific song.                      |
| `POST`          | `/post_story`                   | Post a new story.                            |
| `GET`           | `/stories`                      | Get active stories.                          |
| `DELETE`        | `/delete_expired_stories`       | Delete expired stories.                      |
| `PUT`           | `/profile/{user_id}`            | Update user profile.                         |
| `GET`           | `/profile/{user_id}`            | Get user profile.                            |
| `GET`           | `/tokens/{user_id}`             | Get user token balance.                      |
| `POST`          | `/purchase_tokens`              | Purchase additional tokens.                  |


## Future Enhancements

1. Advanced Music Generation:
    - Support for different music styles and instruments.

2. Social Features:
    - Follow other users and share playlists.

3. Token Refills:
    - Automatically refill tokens daily for premium users.

4. Mobile App:
    - Develop a mobile version of the app using Flutter or React Native.

## Contributors
