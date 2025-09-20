import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_huggingface_api():
    """Test if HuggingFace API is working"""
    
    HF_TOKEN = os.getenv('HF_TOKEN')
    API_URL = "https://api-inference.huggingface.co/models/linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
    
    print(f"HF Token exists: {bool(HF_TOKEN)}")
    print(f"API URL: {API_URL}")
    
    # Create a simple test image
    print("\nCreating test image...")
    img = Image.new('RGB', (224, 224), color='green')
    
    # Save to bytes
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_bytes = buffered.getvalue()
    
    # Prepare headers
    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
        print("Using authentication token")
    else:
        print("No token - using public access")
    
    # Make request
    print("\nSending request to HuggingFace...")
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            data=img_bytes,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            results = response.json()
            print(f"\nSuccess! Got {len(results)} predictions:")
            for i, pred in enumerate(results[:3], 1):
                print(f"{i}. {pred.get('label', 'Unknown')} - {pred.get('score', 0)*100:.2f}%")
        elif response.status_code == 503:
            print("\nModel is loading. Please wait 20-30 seconds and try again.")
            print("Response:", response.json())
        else:
            print(f"\nError: {response.status_code}")
            print("Response:", response.text[:500])
            
    except Exception as e:
        print(f"\nException occurred: {e}")

if __name__ == "__main__":
    test_huggingface_api()