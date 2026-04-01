import requests

def get_location():
    try:
        # Send request to geolocation service
        response = requests.get("http://ip-api.com/json/")
        
        # Convert response to JSON format
        data = response.json()
        
        # Extract latitude and longitude
        latitude = data.get("lat")
        longitude = data.get("lon")
        
        # Return coordinates
        return latitude, longitude
    
    except:
        # If error occurs, return None
        return None, None
if __name__ == "__main__":
    lat, lon = get_location()
    print("Latitude:", lat)
    print("Longitude:", lon)
