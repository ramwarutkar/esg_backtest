import requests
import time

time.sleep(120)
response = requests.get("https://mfdata.in/api/v1/schemes/119709")
print("Status code:", response.status_code)
print("Raw text:", response.text[:300])