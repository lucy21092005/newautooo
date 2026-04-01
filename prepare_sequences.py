import pandas as pd
import numpy as np

# Load dataset
df = pd.read_csv("driver_dataset.csv")

# Features to use
features = [
    "ear",
    "blink_count",
    "closure_duration",
    "phone_detected",
    "distraction_duration"
]

# Convert to numpy
data = df[features].values
labels = df["label"].values

# Sequence length
SEQ_LEN = 20

X = []
y = []

for i in range(len(data) - SEQ_LEN):
    X.append(data[i:i+SEQ_LEN])
    y.append(labels[i+SEQ_LEN])

X = np.array(X)
y = np.array(y)

print("X shape:", X.shape)
print("y shape:", y.shape)

# Save for training
np.save("X.npy", X)
np.save("y.npy", y)

print("✅ Sequences saved (X.npy, y.npy)")