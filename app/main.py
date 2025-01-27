# FastAPI Backend (main.py)
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import psycopg2
import os
from dotenv import load_dotenv
from audiocraft.models import MusicGen
import torchaudio
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm

load_dotenv()

app = FastAPI()

# Database connection
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

# Pydantic models
class SongRequest(BaseModel):
    description: str
    duration: int
    song_name: str

class User(BaseModel):
    username: str
    password: str

@app.on_event("startup")
async def load_model():
    global model
    model = MusicGen.get_pretrained('facebook/musicgen-small')

@app.post("/register/")
async def register(user: User):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists.")

    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (user.username, user.password))
    conn.commit()
    conn.close()
    return {"message": "Registration successful!"}

@app.post("/login/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE username = %s AND password = %s", (form_data.username, form_data.password))
    user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    return {"user_id": user[0], "username": user[1]}

@app.post("/generate/")
async def generate_music(request: SongRequest, user_id: int):
    try:
        # Generate music using the model
        model.set_generation_params(
            use_sampling=True,
            top_k=250,
            duration=request.duration
        )
        output = model.generate(
            descriptions=[request.description],
            progress=True,
            return_tokens=True
        )
        samples = output[0]

        # Save audio as binary
        audio_path = f"audio_output/{request.song_name}.wav"
        torchaudio.save(audio_path, samples[0].detach().cpu(), 32000)

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO songs (user_id, song_name, description, audio_data) VALUES (%s, %s, %s, %s)",
            (user_id, request.song_name, request.description, audio_data),
        )
        conn.commit()
        conn.close()

        return {"message": "Song generated and saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/playlist/")
async def get_playlist(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, song_name, description FROM songs WHERE user_id = %s", (user_id,))
    songs = cursor.fetchall()
    conn.close()
    return {"playlist": songs}

@app.get("/audio/{song_id}")
async def stream_audio(song_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT audio_data FROM songs WHERE id = %s", (song_id,))
    song = cursor.fetchone()
    conn.close()

    if not song:
        raise HTTPException(status_code=404, detail="Song not found.")

    return StreamingResponse(iter([song[0]]), media_type="audio/wav")