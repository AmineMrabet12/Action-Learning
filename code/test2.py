import os
import librosa
import numpy as np
import pandas as pd
from transformers import BertTokenizer, BertModel
import torch
import torchaudio
from torchaudio.transforms import MelSpectrogram
import tensorflow as tf
# from tensorflow.keras.callbacks import EarlyStopping
from openl3 import process_audio

# Load and filter dataset
df = pd.read_csv('data/musiccaps-public.csv')
exist = [file[:-4] for file in os.listdir('data/music_data') if file[:-4] in df['ytid'].values]
filtered_df = df[df['ytid'].isin(exist)]
filtered_df = filtered_df[['ytid', 'caption']]
filtered_df.to_csv('data/filtered.csv')

# 1. Text Preprocessing with Fine-Tuning
def preprocess_text_fine_tune(text_descriptions):
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    model = BertModel.from_pretrained("bert-base-uncased")
    model.train()  # Enable fine-tuning

    embeddings = []
    for text in text_descriptions:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
        with torch.enable_grad():
            outputs = model(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).detach().numpy()
        embeddings.append(cls_embedding)

    return np.array(embeddings)

# 2. Audio Preprocessing using OpenL3

def preprocess_audio_openl3(audio_path, model_type="music", embedding_size=512):
    audio_files = [f + '.wav' for f in audio_path]
    embeddings = []

    for file in audio_files:
        file_path = os.path.join('data/music_data/', file)
        try:
            emb, _ = process_audio(file_path, model_type=model_type, embedding_size=embedding_size)
            embeddings.append(emb)
        except Exception as e:
            print(f"Error processing {file}: {e}")

    return embeddings

# 3. Padding/Truncating Audio Features
def pad_or_truncate(feature, target_shape):
    padded = np.zeros(target_shape, dtype=feature.dtype)
    min_dim0 = min(target_shape[0], feature.shape[0])  # Number of channels
    min_dim1 = min(target_shape[1], feature.shape[1])  # Feature dimension

    padded[:min_dim0, :min_dim1] = feature[:min_dim0, :min_dim1]
    return padded

# Preprocessing the data
def preprocess_data(text_file, target_audio_shape=(2, 2401)):
    text_df = pd.read_csv(text_file)
    text_descriptions = text_df['caption'].tolist()

    print('Starting text embedding with fine-tuning...')
    text_embeddings = preprocess_text_fine_tune(text_descriptions)

    print('Starting audio processing with OpenL3...')
    audio_features = preprocess_audio_openl3(text_df['ytid'])

    audio_features_padded = [
        pad_or_truncate(feature.reshape(feature.shape[0], -1), target_audio_shape) for feature in audio_features
    ]

    return text_embeddings, np.array(audio_features_padded)

# Preprocess with fixed target shape
target_audio_shape = (2, 2401)
# text_embeddings, audio_features_padded = preprocess_data('data/filtered.csv', target_audio_shape)

# Save preprocessed data
# np.save("text_embeddings.npy", text_embeddings)
# np.save("audio_features_padded.npy", audio_features_padded)

text_embeddings = np.load("text_embeddings.npy")
audio_features_padded = np.load("audio_features_padded.npy")

# Normalize data
text_embeddings = (text_embeddings - text_embeddings.mean(axis=0)) / text_embeddings.std(axis=0)
audio_features_padded_resized = (
    audio_features_padded - audio_features_padded.mean(axis=0)
) / audio_features_padded.std(axis=0)

# Model Architecture (Improved)
text_embedding_dim = 768
hidden_dim = 512
seq_len = 2

def create_model():
    text_input = tf.keras.Input(shape=(text_embedding_dim,))
    audio_input = tf.keras.Input(shape=(target_audio_shape[0], target_audio_shape[1]))

    text_hidden = tf.keras.layers.Dense(hidden_dim, activation='relu')(text_input)
    text_hidden = tf.keras.layers.Dropout(0.3)(text_hidden)
    text_rep = tf.keras.layers.RepeatVector(seq_len)(text_hidden)

    audio_hidden = tf.keras.layers.Dense(hidden_dim, activation='relu')(audio_input)

    combined = tf.keras.layers.Concatenate()([text_rep, audio_hidden])
    combined_lstm = tf.keras.layers.LSTM(hidden_dim, return_sequences=True, kernel_regularizer=tf.keras.regularizers.l2(0.01))(combined)

    attention = tf.keras.layers.Attention()([combined_lstm, combined_lstm])
    audio_output = tf.keras.layers.Dense(target_audio_shape[1])(attention)

    model = tf.keras.Model(inputs=[text_input, audio_input], outputs=audio_output)
    return model

model = create_model()
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=tf.keras.optimizers.schedules.ExponentialDecay(
    initial_learning_rate=1e-3, decay_steps=1000, decay_rate=0.9
)), loss='mse')
model.summary()

# Prepare dataset
batch_size = 16
def batch_data(text_embeddings, audio_em, batch_size):
    for i in range(0, len(text_embeddings), batch_size):
        yield (
            text_embeddings[i:i + batch_size],
            audio_em[i:i + batch_size],
        )

train_dataset = tf.data.Dataset.from_generator(
    lambda: batch_data(text_embeddings, audio_features_padded_resized, batch_size),
    output_signature=(
        tf.TensorSpec(shape=(None, text_embedding_dim), dtype=tf.float32),
        tf.TensorSpec(shape=(None, target_audio_shape[0], target_audio_shape[1]), dtype=tf.float32),
    ),
)

# Train the model
early_stopping = EarlyStopping(monitor='loss', patience=10, restore_best_weights=True)
model.fit(train_dataset, epochs=100, callbacks=[early_stopping])
