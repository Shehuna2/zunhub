import requests
from requests.auth import HTTPBasicAuth

url = "https://sandbox.vtpass.com/api/pay"
api_key = "553ffe6309a67bf3c2fb60078bd4d338"  # Replace with actual key
secret_key = "SK_711b0ca303352686aaa414a71208f8f8128c669228a"  # Replace with actual key

payload = {
    "request_id": "test-123",
    "serviceID": "mtn-airtime",
    "amount": 100,
    "phone": "08162037790"
}

response = requests.post(
    url,
    json=payload,
    auth=HTTPBasicAuth(api_key, secret_key),
    headers={"Content-Type": "application/json"}
)

print(response.status_code)
print(response.text)