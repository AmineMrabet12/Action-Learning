# FastAPI Backend (backend.py)
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from audiocraft.models import MusicGen
import torch
from dotenv import load_dotenv
import torchaudio
import os
import base64
from datetime import datetime, timezone, timedelta, date
from typing import Optional

load_dotenv()

# Database configuration
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
    tokens = Column(Integer, default=20)

class Song(Base):
    __tablename__ = 'songs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    song_name = Column(String)
    description = Column(String)
    audio_data = Column(LargeBinary)

class Story(Base):
    __tablename__ = 'stories'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    content = Column(String)  # Could be a URL to an image/video or text
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    expires_at = Column(DateTime)

    # def set_expiration(self):
    #     self.expires_at = self.created_at + timedelta(hours=24)

class UserProfile(Base):
    __tablename__ = 'user_profile'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    dob = Column(Date, nullable=True)
    email = Column(String, unique=True, nullable=False)
    address = Column(String)
    profile_picture = Column(LargeBinary, nullable=True)  # Store image as binary data
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

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
    selected_model: str
    description: str
    duration: int
    song_name: str

class UserProfileUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    dob: Optional[date]
    email: Optional[str]
    address: Optional[str]
    profile_picture: Optional[UploadFile] = None

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


# Helper functions
def save_audio(samples: torch.Tensor, song_name: str):
    sample_rate = 32000
    save_path = "audio_output/"
    audio_path = os.path.join(save_path, f"{song_name}.wav")
    torchaudio.save(audio_path, samples[0].detach().cpu(), sample_rate)
    return audio_path

# Routes
@app.post("/login")
def login(user: UserLogin, db = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username, User.password == user.password).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"user_id": db_user.id, "username": db_user.username}

@app.post("/register")
def register(user: UserRegister, db = Depends(get_db)):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(username=user.username, password=user.password, tokens=20)  # Give 20 tokens on signup
    db.add(new_user)
    db.commit()
    return {"message": "Registration successful"}

@app.post("/generate")
def generate_song(request: SongRequest, user_id: int, db = Depends(get_db)):
    model = MusicGen.get_pretrained(f'facebook/{request.selected_model}')

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.tokens < 10:
        raise HTTPException(status_code=400, detail="Not enough tokens to generate a song")

    model.set_generation_params(use_sampling=True, top_k=250, duration=request.duration)
    
    output = model.generate(descriptions=[request.description], progress=True, return_tokens=True)
    audio_path = save_audio(output[0], request.song_name)
    with open(audio_path, 'rb') as f:
        audio_data = f.read()
    
    if request.selected_model == "musicgen-small":
        user.tokens -= 10
    elif request.selected_model == "musicgen-medium":
        user.tokens -= 20
    elif request.selected_model == "musicgen-large":
        user.tokens -= 30

    db.commit()

    new_song = Song(user_id=user_id, song_name=request.song_name, description=request.description, audio_data=audio_data)
    db.add(new_song)
    db.commit()
    return {"audio_path": audio_path}


@app.get("/playlist")
def get_playlist(user_id: int, db = Depends(get_db)):
    songs = db.query(Song).filter(Song.user_id == user_id).all()
    return [{"id": song.id, "song_name": song.song_name, "description": song.description} for song in songs]

@app.get("/song/{song_id}")
def get_song(song_id: int, db = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    audio_base64 = base64.b64encode(song.audio_data).decode()
    return {"song_name": song.song_name, "description": song.description, "audio_data": audio_base64}

@app.delete("/song/{song_id}")
def delete_song(song_id: int, db = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    db.delete(song)
    db.commit()
    return {"message": "Song deleted successfully"}

###########################################################################
########################### Generate User Story ###########################
###########################################################################

@app.post("/post_story")
def post_story(user_id: int, content: str, db: Session = Depends(get_db)):
    created_at = datetime.now(timezone.utc)  # Current timestamp
    expires_at = created_at + timedelta(hours=24)  # Story expires in 24 hours
    new_story = Story(
        user_id=user_id,
        content=content,
        created_at=created_at,
        expires_at=expires_at
    )
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    return {"message": "Story posted successfully", "story_id": new_story.id}


# Get active stories (those that haven't expired)
@app.get("/stories")
def get_active_stories(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    stories = db.query(Story).filter(Story.expires_at > now).all()
    return stories

# Delete expired stories (could be run periodically, but for now manually)
@app.delete("/delete_expired_stories")
def delete_expired_stories(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    expired_stories = db.query(Story).filter(Story.expires_at <= now).all()
    for story in expired_stories:
        db.delete(story)
    db.commit()
    return {"message": f"{len(expired_stories)} expired stories deleted"}

#############################################################################
########################### Generate User Profile ###########################
#############################################################################

@app.put("/profile/{user_id}")
async def update_or_create_profile(
    user_id: int,
    first_name: str = None,
    last_name: str = None,
    dob: str = None,  # Receive date as string or None
    email: str = None,
    address: str = None,
    profile_picture: UploadFile = File(None),  # Optional profile picture
    db: Session = Depends(get_db),
):
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the user already has a profile
    existing_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    # Initialize the response variable to be used later
    response = None

    # If profile doesn't exist, create a new one
    if not existing_profile:
        # Ensure dob is a valid date string or None
        if dob:
            try:
                # Convert dob to a datetime object if it exists
                dob = datetime.strptime(dob, "%Y-%m-%d").date()  # Expected format "YYYY-MM-DD"
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for 'dob'. Expected 'YYYY-MM-DD'.")

        new_profile = UserProfile(
            user_id=user_id,
            first_name=first_name if first_name else "",  # Set default empty string if None
            last_name=last_name if last_name else "",  # Set default empty string if None
            dob=dob,  # Ensure dob is passed as a valid date or None
            email=email if email else "",  # Set default empty string if None
            address=address if address else "",  # Set default empty string if None
        )

        # Handle profile picture if provided
        if profile_picture:
            # Read image data as binary
            image_data = await profile_picture.read()  # Read the image file as binary data
            new_profile.profile_picture = image_data  # Store as binary
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        response = {"message": "Profile created successfully", "profile": new_profile}

    else:
        # If profile exists, update fields if provided
        if first_name is not None:
            existing_profile.first_name = first_name
        if last_name is not None:
            existing_profile.last_name = last_name
        if dob is not None:
            # Ensure dob is a valid date string or None
            if dob:
                try:
                    # Convert dob to a datetime object if it exists
                    dob = datetime.strptime(dob, "%Y-%m-%d").date()  # Expected format "YYYY-MM-DD"
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid date format for 'dob'. Expected 'YYYY-MM-DD'.")
            existing_profile.dob = dob
        if email is not None:
            existing_profile.email = email
        if address is not None:
            existing_profile.address = address

        # Handle profile picture if provided
        if profile_picture:
            # Read image data as binary
            image_data = await profile_picture.read()  # Read the image file as binary data
            existing_profile.profile_picture = image_data  # Store as binary

        db.commit()
        db.refresh(existing_profile)
        response = {"message": "Profile updated successfully", "profile": existing_profile}

    # Ensure that response is returned after assignment
    if response is None:
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing the profile.")

    return response



@app.get("/profile/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_data = {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "dob": profile.dob,
        "email": profile.email,
        "address": profile.address,
        "profile_picture": base64.b64encode(profile.profile_picture).decode() if profile.profile_picture else None
    }

    return profile_data

#############################################################################
########################### Generate User Tokens  ###########################
#############################################################################
    
# Add these routes to your FastAPI app

@app.get("/tokens/{user_id}")
def get_tokens(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"tokens": user.tokens}

@app.post("/purchase_tokens")
def purchase_tokens(user_id: int, amount: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.tokens is None:
        user.tokens = 0  # Initialize to 0 if it's None

    user.tokens += amount
    db.commit()
    return {"message": "Tokens purchased successfully", "tokens": user.tokens}

