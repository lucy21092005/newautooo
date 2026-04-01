import h5py
import json
import numpy as np
from tensorflow.keras.models import model_from_json
from tensorflow.keras.utils import custom_object_scope

# Load config
with h5py.File("rnn_model.h5", "r") as f:
    model_config = f.attrs.get("model_config")

if isinstance(model_config, bytes):
    model_config = model_config.decode("utf-8")

config = json.loads(model_config)

# 🔥 CLEAN CONFIG FULLY (FINAL FIX)
for layer in config["config"]["layers"]:
    layer_config = layer.get("config", {})

    # FIX INPUT SHAPE
    if "batch_shape" in layer_config:
        shape = layer_config.pop("batch_shape")
        layer_config["input_shape"] = shape[1:]

    # REMOVE ALL PROBLEM KEYS
    layer_config.pop("optional", None)
    layer_config.pop("dtype_policy", None)
    layer_config.pop("quantization_config", None)

    # FORCE dtype
    if "dtype" in layer_config:
        layer_config["dtype"] = "float32"

# Rebuild model safely
with custom_object_scope({}):
    model = model_from_json(json.dumps(config))

# Load weights
model.load_weights("rnn_model.h5")

# ================= RNN =================
SEQ_LEN = 20
feature_buffer = []

def predict_fatigue(feature_vector):
    global feature_buffer

    feature_buffer.append(feature_vector)

    if len(feature_buffer) > SEQ_LEN:
        feature_buffer.pop(0)

    if len(feature_buffer) < SEQ_LEN:
        return None

    sequence = np.array(feature_buffer)
    sequence = np.expand_dims(sequence, axis=0)

    prediction = model.predict(sequence, verbose=0)[0][0]

    return prediction