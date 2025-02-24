import os
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
import requests

from src.etsy_listing_creator.tools.dynamic_mockup import DynamicMockupTool
from src.etsy_listing_creator.tools.stability_ai import StabilityAITool

def test_stability_ai():
    """Test StabilityAI tool with real API calls"""
    print("\n=== Testing StabilityAI Tool ===")
    
    try:
        # Initialize the tool
        print("Initializing tool...")
        tool = StabilityAITool()
        print("✓ Tool initialized successfully")
        
        # Test environment setup
        print("\nChecking environment setup...")
        if not os.getenv("STABILITY_HOST"):
            raise ValueError("STABILITY_HOST environment variable is not set")
        if not os.getenv("STABILITY_KEY"):
            raise ValueError("STABILITY_KEY environment variable is not set")
        if not os.getenv("IMGBB_API_KEY"):
            raise ValueError("IMGBB_API_KEY environment variable is required for image uploading")
        print("✓ Environment variables found")
        
        # Generate and upload an image
        print("\nGenerating and uploading test image...")
        print("This may take a minute...")
        prompt = "A beautiful digital art of a mountain landscape, trending on artstation"
        local_path, public_url = tool.generate_and_upload(prompt)
        
        # Verify result
        print("\nVerifying result...")
        path_obj = Path(local_path)
        if not path_obj.exists():
            print(f"✗ Failed: {local_path} not found")
            return None, None
        else:
            size = path_obj.stat().st_size
            if size < 1000:  # Less than 1KB is suspicious
                print(f"⚠ Warning: {local_path} seems too small ({size} bytes)")
                return None, None
            else:
                print(f"✓ Generated: {local_path} ({size} bytes)")
                print(f"✓ Uploaded to: {public_url}")
                print(f"✓ Prompt used: {prompt}")
                return local_path, public_url
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return None, None

def test_dynamic_mockup(stability_image_info):
    """Test Dynamic Mockups tool with real API calls"""
    print("\n=== Testing Dynamic Mockups Tool ===")
    
    try:
        # Initialize the tool
        print("Initializing tool...")
        tool = DynamicMockupTool()
        print("✓ Tool initialized successfully")
        
        # Test API key
        print("\nTesting API key...")
        api_key = os.getenv("DYNAMIC_MOCKUPS_API_KEY")
        if not api_key:
            raise ValueError("DYNAMIC_MOCKUPS_API_KEY not found in environment variables. Please add it to your .env file.")
        print(f"✓ API key found: {api_key[:10]}...")
        
        if not stability_image_info:
            raise ValueError("No Stability AI image provided")
        
        local_path, public_url = stability_image_info
        print(f"\nUsing Stability AI image: {local_path}")
        print(f"Public URL: {public_url}")
        
        # Test each template
        print("\nTesting templates...")
        for template_name, uuids in tool._templates.items():
            print(f"\nProcessing template: {template_name}")
            print(f"Mockup UUID: {uuids['mockup_uuid']}")
            print(f"Smart Object UUID: {uuids['smart_object_uuid']}")
            
            data = {
                "mockup_uuid": uuids["mockup_uuid"],
                "smart_objects": [
                    {
                        "uuid": uuids["smart_object_uuid"],
                        "asset": {
                            "url": public_url
                        }
                    }
                ]
            }
            
            test_mockup(tool, template_name, data)
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")

def test_mockup(tool, template_name, data):
    """Helper function to test a single mockup generation"""
    print(f"\nMaking API request...")
    print(f"URL: {tool._base_url}/renders")
    print(f"Headers: {tool._get_headers()}")
    print(f"Request Data: {data}")
    
    # Make the API request
    response = requests.post(
        f"{tool._base_url}/renders",
        headers=tool._get_headers(),
        json=data,
        timeout=30
    )
    
    print("\nAPI Response Details:")
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print("Response Body (raw):", response.text)
    
    try:
        response_json = response.json()
        print("\nParsed JSON Response:")
        print(f"Type: {type(response_json)}")
        if isinstance(response_json, dict):
            print(f"Keys: {list(response_json.keys())}")
            print(f"Full content: {response_json}")
        else:
            print(f"Content: {response_json}")
    except Exception as e:
        print(f"Failed to parse JSON response: {str(e)}")
        return
    
    if response.status_code != 200:
        print(f"✗ Request failed with status code: {response.status_code}")
        return
        
    if 'data' not in response_json or 'export_path' not in response_json['data']:
        print("✗ No export_path in response")
        print(f"Response content: {response_json}")
        return
        
    mockup_url = response_json['data']['export_path']
    print(f"✓ Mockup URL received: {mockup_url}")
    
    # Try to download the mockup
    print("\nDownloading mockup...")
    try:
        mockup_response = requests.get(mockup_url)
        if mockup_response.status_code != 200:
            print(f"✗ Download failed with status code: {mockup_response.status_code}")
            return
            
        output_path = tool._output_dir / f"mockup_{template_name}.png"
        with open(output_path, "wb") as f:
            f.write(mockup_response.content)
        
        size = output_path.stat().st_size
        print(f"✓ Mockup saved to: {output_path} ({size} bytes)")
        
    except Exception as e:
        print(f"✗ Failed to download mockup: {str(e)}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run tests
    stability_image_info = test_stability_ai()
    if stability_image_info:
        test_dynamic_mockup(stability_image_info)
    else:
        print("\n✗ Skipping Dynamic Mockups test due to Stability AI failure") 