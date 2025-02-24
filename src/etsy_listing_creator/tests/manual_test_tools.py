import os
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
import requests

from src.etsy_listing_creator.tools.dynamic_mockup import DynamicMockupTool
from src.etsy_listing_creator.tools.stability_ai import StabilityAITool
from src.etsy_listing_creator.tools.claid import ClaidImageTool

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

def test_claid(image_path: str):
    """Test Claid image processing tool to create print-ready images in multiple sizes"""
    print("\n=== Testing Claid Image Processing ===")
    
    # Define standard print sizes (width x height in pixels at 300 DPI)
    PRINT_SIZES = {
        "4x6": (1200, 1800),    # 4x6 inches at 300 DPI
        "5x7": (1500, 2100),    # 5x7 inches at 300 DPI
        "8x10": (2400, 3000),   # 8x10 inches at 300 DPI
        "11x14": (3300, 4200),  # 11x14 inches at 300 DPI
        "16x20": (4800, 6000)   # 16x20 inches at 300 DPI
    }
    
    try:
        # Initialize the tool
        print("Initializing tool...")
        tool = ClaidImageTool()
        print("✓ Tool initialized successfully")
        
        # Test API key
        print("\nTesting API key...")
        api_key = os.getenv("CLAID_API_KEY")
        if not api_key:
            raise ValueError("CLAID_API_KEY not found in environment variables. Please add it to your .env file.")
        print(f"✓ API key found: {api_key[:10]}...")
        
        processed_paths = {}
        
        # Process the image in each size
        print("\nProcessing image in multiple sizes...")
        for size_name, (width, height) in PRINT_SIZES.items():
            print(f"\nProcessing {size_name} size ({width}x{height} pixels)...")
            
            # Prepare request data for print-ready output
            data = {
                "input": image_path,
                "operations": {
                    "resizing": {
                        "fit": "bounds",
                        "width": width,
                        "height": height
                    },
                    "adjustments": {
                        "hdr": {
                            "intensity": 20  # Subtle enhancement for art prints
                        },
                        "sharpness": 25
                    },
                    "restorations": {
                        "upscale": "photo"  # Best for high-quality art upscaling
                    }
                },
                "output": {
                    "metadata": {
                        "dpi": 300  # Print-ready DPI
                    },
                    "format": {
                        "type": "jpeg",
                        "quality": 95,  # High quality for printing
                        "progressive": True
                    }
                }
            }
            
            try:
                processed_path = tool._run_with_data(image_path, data, size_name)
                if processed_path:
                    processed_paths[size_name] = processed_path
                    size = Path(processed_path).stat().st_size
                    print(f"✓ {size_name} processed and saved to: {processed_path} ({size} bytes)")
                else:
                    print(f"✗ Failed to process {size_name} size")
            except Exception as e:
                print(f"✗ Error processing {size_name} size: {str(e)}")
                continue
        
        # Return results
        if processed_paths:
            print(f"\n✓ Successfully processed {len(processed_paths)} sizes")
            return processed_paths
        else:
            print("\n✗ Failed to process any sizes")
            return None
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return None

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
    print("\n=== Starting Test Suite ===")
    
    # Step 1: Generate image with Stability AI
    stability_image_info = test_stability_ai()
    if not stability_image_info:
        print("\n✗ Stability AI test failed. Stopping test suite.")
        exit(1)
    
    local_path, public_url = stability_image_info
    
    # Step 2: Process image with Claid in multiple sizes
    processed_paths = test_claid(local_path)
    if not processed_paths:
        print("\n⚠ Claid processing failed, but continuing with mockup generation...")
    else:
        print("\nProcessed images:")
        for size, path in processed_paths.items():
            print(f"- {size}: {path}")
    
    # Step 3: Generate mockups using original Stability AI image
    test_dynamic_mockup(stability_image_info)
    
    print("\n=== Test Suite Complete ===") 