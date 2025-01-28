# FastAPI Backend (backend.py)
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from audiocraft.models import MusicGen
import torch
from dotenv import load_dotenv
import torchaudio
import os
import base64

load_dotenv()

# Database configuration
# DATABASE_URL = "postgresql+psycopg2://amine:amine@localhost:5432/epita"
DATABASE_URL = os.getenv('DATABASE_URL')
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Models
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

class Song(Base):
    __tablename__ = 'songs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    song_name = Column(String)
    description = Column(String)
    audio_data = Column(LargeBinary)

Base.metadata.create_all(bind=engine)

# Pydantic Models
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    confirm_password: str

class SongRequest(BaseModel):
    description: str
    duration: int
    song_name: str

# App Initialization
app = FastAPI()

# Dependency
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Load MusicGen model
model = MusicGen.get_pretrained('facebook/musicgen-small')

# Helper functions
def save_audio(samples: torch.Tensor, song_name: str):
    sample_rate = 32000
    save_path = "audio_output/"
    audio_path = os.path.join(save_path, f"{song_name}.wav")
    torchaudio.save(audio_path, samples[0].detach().cpu(), sample_rate)
    return audio_path

# Routes
@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username, User.password == user.password).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"user_id": db_user.id, "username": db_user.username}

@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(username=user.username, password=user.password)
    db.add(new_user)
    db.commit()
    return {"message": "Registration successful"}

@app.post("/generate")
def generate_song(request: SongRequest, user_id: int, db: Session = Depends(get_db)):
    model.set_generation_params(use_sampling=True, top_k=250, duration=request.duration)
    output = model.generate(descriptions=[request.description], progress=True, return_tokens=True)
    audio_path = save_audio(output[0], request.song_name)
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    new_song = Song(user_id=user_id, song_name=request.song_name, description=request.description, audio_data=audio_data)
    db.add(new_song)
    db.commit()
    return {"audio_path": audio_path}

@app.get("/playlist")
def get_playlist(user_id: int, db: Session = Depends(get_db)):
    songs = db.query(Song).filter(Song.user_id == user_id).all()
    return [{"id": song.id, "song_name": song.song_name, "description": song.description} for song in songs]

@app.get("/song/{song_id}")
def get_song(song_id: int, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    audio_base64 = base64.b64encode(song.audio_data).decode()
    return {"song_name": song.song_name, "description": song.description, "audio_data": audio_base64}