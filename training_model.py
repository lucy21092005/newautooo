import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# Load dataset
data = pd.read_csv("driver_behavior_log.csv",on_bad_lines="skip")

# Features
X = data[[
    "ear",
    "blink_count",
    "eye_closure_duration",
    "phone_detected",
    "distraction_duration"
]]

# Better label logic
y = []

for _, row in data.iterrows():
    risk_score = 0

    if row["eye_closure_duration"] > 1.5:
        risk_score += 2

    if row["distraction_duration"] > 2.0:
        risk_score += 2

    if row["ear"] < 0.20:
        risk_score += 2

    if row["phone_detected"] == 1:
        risk_score += 1

    if row["blink_count"] > 20:
        risk_score += 1

    # Final classification
    if risk_score <= 2:
        y.append(0)   # SAFE
    elif risk_score <= 4:
        y.append(1)   # WARNING
    else:
        y.append(2)   # DANGER

# Train model
model = RandomForestClassifier(n_estimators=150, random_state=42)
model.fit(X, y)

# Save model
joblib.dump(model, "driver_risk_model.pkl")

print("✅ Model trained and saved!")