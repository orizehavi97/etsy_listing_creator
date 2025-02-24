import os
from pathlib import Path
from typing import Dict

import requests
from PIL import Image
from pydantic import Field, PrivateAttr

from crewai.tools import BaseTool

class ClaidImageTool(BaseTool):
    name: str = "Claid Image Processor"
    description: str = """
    Process images to meet print quality standards using Claid.ai API.
    Input should be a path to an image file.
    Returns the path to the processed image file.
    """

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()
    _output_dir: Path = PrivateAttr()
    _base_url: str = PrivateAttr(default="https://api.claid.ai")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("CLAID_API_KEY")
        if not self._api_key:
            raise ValueError("CLAID_API_KEY environment variable is required")
        
        self._output_dir = Path("output/processed_images")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _get_headers(self) -> Dict[str, str]:
        """Get required headers for API requests"""
        return {
            "Host": "api.claid.ai",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

    def _run(self, image_path: str) -> str:
        """
        Process an image using Claid.ai API.
        
        Args:
            image_path: Path to the input image file
            
        Returns:
            Path to the processed image file
        """
        # Get original image dimensions and format
        with Image.open(image_path) as img:
            width, height = img.size
            # Calculate target dimensions (maintaining aspect ratio)
            target_width = 2048  # Standard high-quality width
            target_height = int((target_width / width) * height)

        # Prepare the API request data
        data = {
            "input": image_path,  # Will be replaced with file upload or URL
            "operations": {
                "resizing": {
                    "fit": "bounds",
                    "width": target_width,
                    "height": target_height
                },
                "adjustments": {
                    "hdr": {
                        "intensity": 100
                    },
                    "sharpness": 25
                },
                "restorations": {
                    "upscale": "smart_enhance"
                }
            },
            "output": {
                "format": {
                    "type": "jpeg",
                    "quality": 85,
                    "progressive": True
                }
            }
        }

        try:
            # First, upload the image or get a signed URL
            with open(image_path, "rb") as img_file:
                files = {"file": (Path(image_path).name, img_file, "image/jpeg")}
                upload_response = requests.post(
                    f"{self._base_url}/v1-beta1/upload",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files=files
                )
                
                if upload_response.status_code != 200:
                    raise RuntimeError(f"Failed to upload image: {upload_response.text}")
                
                # Get the URL of the uploaded image
                upload_result = upload_response.json()
                data["input"] = upload_result["url"]

            # Process the image
            response = requests.post(
                f"{self._base_url}/v1-beta1/image/edit",
                headers=self._get_headers(),
                json=data
            )

            if response.status_code != 200:
                raise RuntimeError(f"Failed to process image: {response.text}")

            # Get the processed image URL from the response
            result = response.json()
            if "url" not in result:
                raise RuntimeError("No processed image URL in response")

            # Download the processed image
            processed_response = requests.get(result["url"])
            if processed_response.status_code != 200:
                raise RuntimeError("Failed to download processed image")

            # Save the processed image
            output_path = self._output_dir / f"processed_{Path(image_path).stem}.jpg"
            with open(output_path, "wb") as f:
                f.write(processed_response.content)

            # Verify the DPI of the processed image
            with Image.open(output_path) as img:
                if "dpi" in img.info and img.info["dpi"][0] < 300:
                    raise ValueError("Failed to achieve required DPI")

            return str(output_path)

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API request failed: {str(e)}") 