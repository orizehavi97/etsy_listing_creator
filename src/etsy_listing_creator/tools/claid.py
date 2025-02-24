import os
from pathlib import Path
from typing import List

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("CLAID_API_KEY")
        if not self._api_key:
            raise ValueError("CLAID_API_KEY environment variable is required")
        
        self._output_dir = Path("output/processed_images")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _run(self, image_path: str) -> str:
        """
        Process an image using Claid.ai API.
        
        Args:
            image_path: Path to the input image file
            
        Returns:
            Path to the processed image file
        """
        # Prepare the API request
        url = "https://api.claid.ai/v1/image/process"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        # Load and prepare the image
        with open(image_path, "rb") as img_file:
            files = {
                "image": ("image.png", img_file, "image/png")
            }

        # Process parameters for print quality
        params = {
            "upscale": True,
            "upscale_factor": 2,
            "dpi": 300,
            "format": "png",
            "quality": 100,
            "color_profile": "srgb"
        }

        # Make the API request
        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=params
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to process image: {response.text}")

        # Save the processed image
        output_path = self._output_dir / f"processed_{Path(image_path).stem}.png"
        with open(output_path, "wb") as f:
            f.write(response.content)

        # Verify the image was processed correctly
        img = Image.open(output_path)
        if img.info.get("dpi", (72, 72))[0] < 300:
            raise ValueError("Failed to achieve required DPI")

        return str(output_path) 