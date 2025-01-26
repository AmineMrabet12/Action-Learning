import os
import numpy as np
import torch
from transformers import BertTokenizer, BertModel
import librosa
import tensorflow as tf
from librosa.feature.inverse import mel_to_audio
# from librosa.output import write_wav
import soundfile as sf


# Load the trained model
model = tf.keras.models.load_model("model.h5", compile=False)
model.compile(optimizer="adam", loss="mse")   # Recompile manually

# model = tf.keras.models.load_model("model.h5", custom_objects={"mse": tf.keras.losses.MeanSquaredError()})

# Load preprocessing functions
def preprocess_single_text(description):
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertModel.from_pretrained("bert-base-uncased")

    inputs = tokenizer(description, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)

    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).numpy()
    
    return np.expand_dims(cls_embedding, axis=0)  # Add batch dimension

# Convert model output back to audio
def postprocess_audio_features(features, output_path, target_sr=16000, n_mels=128):
    features = features.squeeze()  # Remove batch dimension
    mel_spec = features.T  # Transpose to match Mel spectrogram format
    mel_spec_db = librosa.db_to_power(mel_spec, ref=1.0)  # Convert back from log scale
    waveform = librosa.feature.inverse.mel_to_audio(mel_spec_db, sr=target_sr, n_fft=2048, hop_length=512, n_mels=n_mels)

    librosa.output.write_wav(output_path, waveform, sr=target_sr)

# Inference function
def generate_audio_from_text(description, output_path):
    print("Preprocessing text description...")
    text_embedding = preprocess_single_text(description)
    
    print("Generating audio features...")
    predicted_features = model.predict(text_embedding)
    
    print("Post-processing and saving audio...")
    postprocess_audio_features(predicted_features, output_path)

    print(f"Audio saved to {output_path}")

# Example usage
text_description = "A soothing piano melody with soft background strings."
output_audio_path = "generated_audio.wav"
generate_audio_from_text(text_description, output_audio_path)


# sf.write(output_audio_path, waveform, sr=target_sr)