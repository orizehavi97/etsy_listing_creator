import os
from pathlib import Path
from typing import Dict, List

import requests
from PIL import Image
from pydantic import Field, PrivateAttr

from crewai.tools import BaseTool

class ClaidImageTool(BaseTool):
    name: str = "Claid Image Processor"
    description: str = """
    Process images to meet print quality standards using Claid.ai API.
    Input should be a path to an image file.
    Returns a list of paths to the processed image files in different sizes.
    """

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()
    _imgbb_key: str = PrivateAttr()
    _output_dir: Path = PrivateAttr()
    _base_url: str = PrivateAttr(default="https://api.claid.ai")
    
    # Standard print sizes in inches at 300 DPI
    _print_sizes: Dict[str, Dict[str, int]] = PrivateAttr(default={
        "4x6": {"width": 1200, "height": 1800},     # 4x6 inches at 300 DPI
        "5x7": {"width": 1500, "height": 2100},     # 5x7 inches at 300 DPI
        "8x10": {"width": 2400, "height": 3000},    # 8x10 inches at 300 DPI
        "11x14": {"width": 3300, "height": 4200},   # 11x14 inches at 300 DPI
        "16x20": {"width": 4800, "height": 6000},   # 16x20 inches at 300 DPI
    })

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("CLAID_API_KEY")
        self._imgbb_key = os.getenv("IMGBB_API_KEY")
        if not self._api_key:
            raise ValueError("CLAID_API_KEY environment variable is required")
        if not self._imgbb_key:
            raise ValueError("IMGBB_API_KEY environment variable is required for image uploading")
        
        self._output_dir = Path("output/processed_images")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _get_headers(self) -> Dict[str, str]:
        """Get required headers for API requests"""
        return {
            "Host": "api.claid.ai",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

    def _upload_to_imgbb(self, image_path: str) -> str:
        """Upload image to ImgBB and get public URL"""
        print(f"Uploading image to ImgBB: {image_path}")
        
        with open(image_path, "rb") as img_file:
            import base64
            image_data = base64.b64encode(img_file.read()).decode('utf-8')
        
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": self._imgbb_key,
                "image": image_data,
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Failed to upload to ImgBB: {response.text}")
        
        result = response.json()
        if not result.get('success'):
            raise RuntimeError(f"ImgBB upload failed: {result}")
        
        url = result['data']['url']
        print(f"✓ Image uploaded to: {url}")
        return url

    def _run_with_data(self, image_path: str, data: Dict, size_name: str) -> str:
        """
        Process an image using Claid.ai API with custom data and size-specific output.
        
        Args:
            image_path: Path to the input image file
            data: Custom processing parameters
            size_name: Name of the size being processed (for output filename)
            
        Returns:
            Path to the processed image file
        """
        try:
            # First upload the image to get a public URL
            image_url = self._upload_to_imgbb(image_path)
            
            # Update the request data with the image URL
            data["input"] = image_url

            # Process the image
            print(f"\nMaking request to {self._base_url}/v1-beta1/image/edit")
            print(f"Request data: {data}")
            response = requests.post(
                f"{self._base_url}/v1-beta1/image/edit",
                headers=self._get_headers(),
                json=data,
                timeout=60  # Increased timeout for large images
            )

            if response.status_code != 200:
                print(f"Error response: {response.text}")
                raise RuntimeError(f"Failed to process image: {response.text}")

            # Parse the response
            result = response.json()
            if not result.get('data', {}).get('output', {}).get('tmp_url'):
                raise RuntimeError("No output URL in response")

            # Get the processed image URL
            processed_url = result['data']['output']['tmp_url']
            print(f"✓ Processed image URL: {processed_url}")

            # Download the processed image
            processed_response = requests.get(processed_url)
            if processed_response.status_code != 200:
                raise RuntimeError("Failed to download processed image")

            # Save the processed image with size in filename
            output_path = self._output_dir / f"processed_{Path(image_path).stem}_{size_name}.jpg"
            with open(output_path, "wb") as f:
                f.write(processed_response.content)

            # Verify the image was saved
            if not output_path.exists():
                raise RuntimeError("Failed to save processed image")

            size = output_path.stat().st_size
            print(f"✓ Saved image size: {size} bytes")

            return str(output_path)

        except Exception as e:
            print(f"Error details: {str(e)}")
            raise RuntimeError(f"API request failed: {str(e)}")

    def _run(self, image_path: str) -> List[str]:
        """
        Process an image using Claid.ai API with multiple size outputs.
        
        Args:
            image_path: Path to the input image file
            
        Returns:
            List of paths to the processed image files
        """
        processed_paths = []
        
        # Get original image dimensions and aspect ratio
        with Image.open(image_path) as img:
            orig_width, orig_height = img.size
            aspect_ratio = orig_width / orig_height

        # Process each standard size
        for size_name, dimensions in self._print_sizes.items():
            print(f"\nProcessing {size_name} size...")
            
            # Adjust dimensions to maintain aspect ratio
            target_width = dimensions["width"]
            target_height = dimensions["height"]
            
            # Calculate dimensions that maintain original aspect ratio
            if aspect_ratio > target_width / target_height:
                # Width limited
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                # Height limited
                new_height = target_height
                new_width = int(target_height * aspect_ratio)

            # Prepare the processing data
            data = {
                "operations": {
                    "resizing": {
                        "fit": "bounds",
                        "width": new_width,
                        "height": new_height
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
                    "metadata": {
                        "dpi": 300
                    },
                    "format": {
                        "type": "jpeg",
                        "quality": 85,
                        "progressive": True
                    }
                }
            }

            # Process the image for this size
            try:
                processed_path = self._run_with_data(image_path, data, size_name)
                processed_paths.append(processed_path)
                print(f"✓ Successfully processed {size_name} size")
            except Exception as e:
                print(f"✗ Failed to process {size_name} size: {str(e)}")
                continue

        if not processed_paths:
            raise RuntimeError("Failed to process any image sizes")

        return processed_paths 