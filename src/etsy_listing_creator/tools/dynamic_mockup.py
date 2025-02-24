import os
from pathlib import Path
from typing import List, Dict

import requests
from pydantic import Field, PrivateAttr

from crewai.tools import BaseTool

class DynamicMockupTool(BaseTool):
    name: str = "Dynamic Mockups Generator"
    description: str = """
    Create professional product mockups using Dynamic Mockups API.
    Input should be a path to an image file.
    Returns a list of paths to the generated mockup files.
    """

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()
    _output_dir: Path = PrivateAttr()
    _base_url: str = PrivateAttr(default="https://app.dynamicmockups.com/api/v1")
    _templates: Dict[str, Dict[str, str]] = PrivateAttr(default={
        "frame-mockup": {
            "mockup_uuid": "88ad0ec7-4b34-4be4-a762-154d64229d07",
            "smart_object_uuid": "89f5a078-8770-4cb8-9e53-acdd45663c76"
        }
    })

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("DYNAMIC_MOCKUPS_API_KEY")
        if not self._api_key:
            raise ValueError("DYNAMIC_MOCKUPS_API_KEY environment variable is required")
        
        self._output_dir = Path("output/mockups")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _get_headers(self) -> Dict[str, str]:
        """Get required headers for API requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self._api_key
        }

    def _handle_error_response(self, response: requests.Response, template_name: str = None) -> None:
        """Handle error responses from the API"""
        try:
            error_data = response.json()
            error_message = error_data.get('message', '')
            error_details = error_data.get('errors', {})
            print(f"Error response: {error_data}")  # Add more detailed error logging
        except:
            error_message = response.text
            error_details = {}
            print(f"Raw error response: {response.text}")  # Add raw error logging

        if response.status_code == 401:
            raise ValueError("Unauthorized - Invalid API key")
        elif response.status_code == 422:
            if 'mockup_uuid' in error_details:
                raise ValueError(f"Invalid mockup UUID: {error_message}")
            else:
                raise ValueError(f"Validation error: {error_message}")
        elif response.status_code == 429:
            raise RuntimeError("Rate limit exceeded (300 calls per minute)")
        elif response.status_code == 400:
            if template_name:  # Partial failure
                return None
            else:  # Complete failure
                raise RuntimeError(f"Bad request: {error_message}")
        elif response.status_code >= 500:
            raise RuntimeError("Server error occurred. Please try again later.")
        else:  # Other errors
            raise RuntimeError(f"API request failed ({response.status_code}): {error_message}")

    def _run(self, image_path: str) -> List[str]:
        """
        Generate product mockups using Dynamic Mockups API.
        
        Args:
            image_path: Path to the input image file
            
        Returns:
            List of paths to the generated mockup files
        """
        mockup_paths = []

        # Generate mockups for each template
        for template_name, uuids in self._templates.items():
            try:
                print(f"\nProcessing template: {template_name}")
                # For now, we'll use the sandbox image URL
                # In production, you would need to upload your image to a public URL first
                image_url = "https://app-dynamicmockups-production.s3.eu-central-1.amazonaws.com/static/api_sandbox_icon.png"
                
                # Prepare the mockup request data
                data = {
                    "mockup_uuid": uuids["mockup_uuid"],
                    "smart_objects": [
                        {
                            "uuid": uuids["smart_object_uuid"],
                            "asset": {
                                "url": "https://app-dynamicmockups-production.s3.eu-central-1.amazonaws.com/static/api_sandbox_icon.png"
                            }
                        }
                    ]
                }

                print(f"Making API request to {self._base_url}/renders")
                print(f"Request data: {data}")
                print(f"Request headers: {self._get_headers()}")
                
                # Generate the mockup
                response = requests.post(
                    f"{self._base_url}/renders",
                    headers=self._get_headers(),
                    json=data,
                    timeout=30  # Add timeout to prevent hanging
                )

                print("\nAPI Response Details:")
                print(f"Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                print("Response Body (raw):", response.text)
                
                try:
                    result = response.json()
                    print("\nParsed JSON Response:")
                    print(f"Type: {type(result)}")
                    if isinstance(result, dict):
                        print(f"Keys: {list(result.keys())}")
                        print(f"Full content: {result}")
                    else:
                        print(f"Content: {result}")
                except Exception as e:
                    print(f"Failed to parse JSON response: {str(e)}")
                    continue

                # Handle unsuccessful responses
                if response.status_code != 200:
                    self._handle_error_response(response, template_name)
                    continue

                # Parse the response
                result = response.json()
                print(f"Parsed response: {result}")

                if isinstance(result, dict):
                    if 'data' not in result or 'export_path' not in result['data']:
                        print("✗ Error: Response does not contain export_path")
                        print(f"Response content: {result}")
                        continue
                    
                    mockup_url = result['data']['export_path']
                    print(f"Mockup URL received: {mockup_url}")
                else:
                    print("✗ Error: Response is not a dictionary")
                    print(f"Response content: {result}")
                    continue
                
                # Download mockup
                print("Downloading mockup...")
                mockup_response = requests.get(mockup_url)
                if mockup_response.status_code != 200:
                    print(f"✗ Download failed with status code: {mockup_response.status_code}")
                    print(f"Download error: {mockup_response.text}")
                    continue
                    
                output_path = self._output_dir / f"mockup_{template_name}.png"
                with open(output_path, "wb") as f:
                    f.write(mockup_response.content)
                
                size = output_path.stat().st_size
                print(f"✓ Mockup saved to: {output_path} ({size} bytes)")
                mockup_paths.append(str(output_path))

            except requests.exceptions.RequestException as e:
                print(f"✗ Network error for template {template_name}: {str(e)}")
                continue
            except Exception as e:
                print(f"✗ Unexpected error for template {template_name}: {str(e)}")
                continue

        if not mockup_paths:
            raise RuntimeError("Failed to generate any mockups. Please check your API key and template UUIDs.")

        return mockup_paths 