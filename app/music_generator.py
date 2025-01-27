import streamlit as st
import torch
import torchaudio
from audiocraft.models import MusicGen
import base64
import os
from auth import save_song_to_db  # Import the function from auth.py

@st.cache_resource
def load_model():
    model = MusicGen.get_pretrained('facebook/musicgen-small')
    return model

def generate_music_tensors(description, duration: int):
    print("Description: ", description)
    print("Duration: ", duration)
    model = load_model()

    model.set_generation_params(
        use_sampling=True,
        top_k=250,
        duration=duration
    )

    output = model.generate(
        descriptions=[description],
        progress=True,
        return_tokens=True
    )

    return output[0]

def save_audio(samples: torch.Tensor, song_name: str, description: str):
    """Save the generated audio and save details to the database"""
    sample_rate = 32000
    save_path = "audio_output/"
    assert samples.dim() == 2 or samples.dim() == 3

    samples = samples.detach().cpu()
    if samples.dim() == 2:
        samples = samples[None, ...]

    # Save audio as binary data
    audio_path = os.path.join(save_path, f"{song_name}.wav")
    torchaudio.save(audio_path, samples[0], sample_rate)

    # Read the audio file as binary data
    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    # Save song details and audio data to the database
    save_song_to_db(st.session_state.user_id, song_name, description, audio_data)

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href
