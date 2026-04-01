from flask import Flask, request, jsonify
from device_id_manager import get_device_id

app = Flask(__name__)

DEVICE_ID = get_device_id()


@app.route('/')
def home():
    return "AutoGuardian-X ADMS Server Running"


@app.route('/connect/<device_id>', methods=['GET'])
def connect_device(device_id):

    if device_id == DEVICE_ID:
        return jsonify({
            "status": "connected",
            "device_id": DEVICE_ID
        })

    return jsonify({
        "status": "invalid_device"
    })
@app.route('/driver_status/<device_id>', methods=['GET'])
def driver_status(device_id):

    print("Driver status requested for:", device_id)

    if device_id != DEVICE_ID:
        return jsonify({"status": "invalid_device"})

    return jsonify({
        "device_id": DEVICE_ID,
        "driver_state": "safe",
        "risk_score": 0.12,
        "event": "normal_driving"
    })

    return jsonify(data)


@app.route('/emergency', methods=['POST'])
def emergency_trigger():

    data = request.json

    print("🚨 EMERGENCY SIGNAL RECEIVED")
    print(data)

    return jsonify({
        "status": "received",
        "message": "Emergency event logged"
    })
import os


if __name__ == "__main__":

    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(rule)
        port = int(os.environ.get("PORT",5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )