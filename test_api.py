import requests
import json

# Test the API endpoint
url = "http://localhost:8000/api/process-criteria"
data = {
    "criteria_text": """INCLUSION CRITERIA:
1. Adults aged 18 to 75 years
2. Type 2 Diabetes Mellitus diagnosis

EXCLUSION CRITERIA:
1. History of heart failure"""
}

print("Testing API endpoint...")
print(f"URL: {url}")
print(f"Data: {json.dumps(data, indent=2)}")
print("\nSending request...")

try:
    response = requests.post(url, json=data, timeout=120)
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ SUCCESS!")
        print(f"Stages completed: {len(result.get('stages', []))}")
        print(f"Final cohort size: {result.get('execution_result', {}).get('execution_summary', {}).get('n', 'N/A')}")
    else:
        print(f"\n❌ ERROR: {response.text}")
except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
