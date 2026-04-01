import requests

def check_mobile_connection():
    phone_ip = "10.253.40.138"
    url = f"http://{phone_ip}:8080/health"
    
    try:
        response = requests.get(url, timeout=1)
        return response.text == "OK"
    except Exception:
        return False

def trigger_mobile_emergency():

    phone_ip = "10.253.40.138"   # your phone IP

    url = f"http://{phone_ip}:8080/trigger"

    try:
        response = requests.get(url, timeout=3)

        print("📡 Mobile emergency triggered")
        print(response.text)

    except Exception as e:
        print("❌ Failed to trigger mobile emergency:", e)