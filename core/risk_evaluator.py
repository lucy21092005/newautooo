import pandas as pd

MODEL_FEATURES = [
    "ear",
    "blink_count",
    "eye_closure_duration",
    "phone_detected",
    "distraction_duration"
]
class RiskEvaluator:
    def __init__(self, model_manager):
        self.model_manager = model_manager


def evaluate(self, perception_data):

    ear = perception_data["ear"]
    blink_count = perception_data["blink_count"]
    closure_duration = perception_data["closure_duration"]
    phone_detected = perception_data["phone_detected"]
    distraction_duration = perception_data["distraction_duration"]

    features = pd.DataFrame(
        [[
            ear,
            blink_count,
            closure_duration,
            phone_detected,
            distraction_duration
        ]],
        columns=MODEL_FEATURES
    )

    model = self.model_manager.get_model()

    prediction = model.predict(features)[0]

    # 🔥 MAP CLASS → RISK SCORE
    if prediction == 0:
        risk_score = 20
        risk_level = "LOW"
        risk_color = (0, 255, 0)
    elif prediction == 1:
        risk_score = 60
        risk_level = "MEDIUM"
        risk_color = (0, 165, 255)
    else:
        risk_score = 90
        risk_level = "HIGH"
        risk_color = (0, 0, 255)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "system_status": "ACTIVE"
    }