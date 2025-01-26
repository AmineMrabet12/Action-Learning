import os
import librosa
import numpy as np
import pandas as pd
from transformers import BertTokenizer, BertModel
import torch
import torchaudio
from torchaudio.transforms import MelSpectrogram
import tensorflow as tf


# Load and filter dataset
df = pd.read_csv('data/musiccaps-public.csv')
exist = [file[:-4] for file in os.listdir('data/music_data') if file[:-4] in df['ytid'].values]
filtered_df = df[df['ytid'].isin(exist)]
filtered_df = filtered_df[['ytid', 'caption']]
filtered_df.to_csv('data/filtered.csv')


# 1. Text Preprocessing
def preprocess_text(text_descriptions):
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertModel.from_pretrained("bert-base-uncased")
    embeddings = []

    for text in text_descriptions:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).numpy()
        embeddings.append(cls_embedding)
    
    return np.array(embeddings)


# 2. Audio Preprocessing
def preprocess_audio(audio_path, target_sr=16000, n_mels=128):
    audio_files = [f+'.wav' for f in audio_path]
    spectrograms = []

    for file in audio_files:
        file_path = os.path.join('data/music_data/', file)
        try:
            waveform, sample_rate = torchaudio.load(file_path)

            transform = MelSpectrogram(sample_rate=sample_rate, n_mels=n_mels)
            mel_spec = transform(waveform)

            log_mel_spec = librosa.power_to_db(mel_spec.numpy(), ref=np.max)
            spectrograms.append(log_mel_spec)

        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    return spectrograms


# 3. Padding/Truncating Audio Features
def pad_or_truncate(feature, target_shape):
    """
    Pads or truncates a 2D feature array to match the target shape.
    Args:
        feature (numpy array): Input feature array (expected shape: (channels, feature_dim)).
        target_shape (tuple): Target shape, e.g., (2, 2401).
    Returns:
        numpy array: Feature padded or truncated to the target shape.
    """
    padded = np.zeros(target_shape, dtype=feature.dtype)
    min_dim0 = min(target_shape[0], feature.shape[0])  # Number of channels
    min_dim1 = min(target_shape[1], feature.shape[1])  # Feature dimension
    
    # Copy data into the padded array
    padded[:min_dim0, :min_dim1] = feature[:min_dim0, :min_dim1]
    return padded


# Preprocessing the data
def preprocess_data(text_file, target_audio_shape=(2, 2401)):
    text_df = pd.read_csv(text_file)
    text_descriptions = text_df['caption'].tolist()

    print('Starting text embedding...')
    text_embeddings = preprocess_text(text_descriptions)

    print('Starting audio processing...')
    audio_features = preprocess_audio(text_df['ytid'])
    
    # Flatten audio features and then pad or truncate
    audio_features_padded = [
        pad_or_truncate(feature.reshape(feature.shape[0], -1), target_audio_shape) for feature in audio_features
    ]

    return text_embeddings, np.array(audio_features_padded)


# Preprocess with fixed target shape
target_audio_shape = (2, 2401)  # Match the model's output shape
# text_embeddings, audio_features_padded = preprocess_data('data/filtered.csv', target_audio_shape)

# Save preprocessed data
# np.save("text_embeddings.npy", text_embeddings)
# np.save("audio_features_padded.npy", audio_features_padded)

text_embeddings = np.load("text_embeddings.npy")
audio_features_padded = np.load("audio_features_padded.npy")


# Model Architecture (using layers)
text_embedding_dim = 768  
audio_feature_dim = 2401  
hidden_dim = 512
seq_len = 2  


audio_features_padded_resized = audio_features_padded.reshape(audio_features_padded.shape[0], 2, -1)

text_input = tf.keras.Input(shape=(text_embeddings.shape[1],))
audio_input = tf.keras.Input(shape=(target_audio_shape[0], target_audio_shape[1]))

text_hidden = tf.keras.layers.Dense(hidden_dim, activation='relu')(text_input)
text_rep = tf.keras.layers.RepeatVector(seq_len)(text_hidden)
lstm_out = tf.keras.layers.LSTM(hidden_dim, return_sequences=True)(text_rep)
audio_output = tf.keras.layers.Dense(target_audio_shape[1])(lstm_out)

model = tf.keras.Model(inputs=text_input, outputs=audio_output)
model.compile(optimizer='adam', loss='mse')
model.summary()


batch_size = 16

def batch_data(text_embeddings, audio_em, batch_size):
    for i in range(0, len(text_embeddings), batch_size):
        yield text_embeddings[i:i+batch_size], audio_em[i:i+batch_size]

train_dataset = tf.data.Dataset.from_generator(
    lambda: batch_data(text_embeddings, audio_features_padded_resized, batch_size),
    output_signature=(
        tf.TensorSpec(shape=(None, text_embeddings.shape[1]), dtype=tf.float32),
        tf.TensorSpec(shape=(None, target_audio_shape[0], target_audio_shape[1]), dtype=tf.float32)
    )
)


model.fit(train_dataset, epochs=100)

model.save('model.h5')
# model.save("model_saved", save_format="tf")
