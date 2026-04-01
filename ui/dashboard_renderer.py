import cv2


class DashboardRenderer:

    def __init__(self):
        pass


    def render(self, frame, perception_data, risk_data):

        risk_level = risk_data["risk_level"]
        risk_score = risk_data["risk_score"]
        risk_color = risk_data["risk_color"]

        drowsiness_status = perception_data["drowsiness_status"]
        phone_status = perception_data["phone_status"]
        blink_count = perception_data["blink_count"]
        closure_duration = perception_data["closure_duration"]
        distraction_duration = perception_data["distraction_duration"]

        y = 30
        gap = 30

        cv2.putText(frame, "AUTO-GUARDIAN-X", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        y += gap

        

        cv2.putText(frame, f"Risk Level: {risk_level}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, risk_color, 2)
        y += gap

        cv2.putText(frame, f"Risk Score: {risk_score:.1f}%", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, risk_color, 2)
        y += gap

        cv2.putText(frame, f"Drowsiness: {drowsiness_status}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        y += gap

        cv2.putText(frame, f"Phone: {phone_status}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
        y += gap

        cv2.putText(frame, f"Blinks: {blink_count}", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
        y += gap

        cv2.putText(frame, f"Closure: {closure_duration:.2f}s", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
        y += gap

        cv2.putText(frame, f"Distraction: {distraction_duration:.2f}s", (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,200,255), 2)
