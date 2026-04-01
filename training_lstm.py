import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Load data
X = np.load("X.npy")
y = np.load("y.npy")

print("Data loaded:", X.shape, y.shape)

# Build model
model = Sequential([
    LSTM(32, input_shape=(X.shape[1], X.shape[2])),
    Dropout(0.2),
    Dense(16, activation='relu'),
    Dense(1, activation='sigmoid')
])

model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy']
)

# Train model
model.fit(
    X, y,
    epochs=10,
    batch_size=32,
    validation_split=0.2
)

# Save model
model.save("rnn_model.h5")

print("✅ Model trained and saved as rnn_model.h5")