import os
from pathlib import Path
from typing import List

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
    _templates: List[str] = PrivateAttr(default=[
        "frame-on-wall",
        "frame-on-desk",
        "gallery-wall",
        "living-room-scene"
    ])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("DYNAMIC_MOCKUPS_API_KEY")
        if not self._api_key:
            raise ValueError("DYNAMIC_MOCKUPS_API_KEY environment variable is required")
        
        self._output_dir = Path("output/mockups")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _run(self, image_path: str) -> List[str]:
        """
        Generate product mockups using Dynamic Mockups API.
        
        Args:
            image_path: Path to the input image file
            
        Returns:
            List of paths to the generated mockup files
        """
        mockup_paths = []

        # Load the image
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()

        # Generate mockups for each template
        for template in self._templates:
            # Prepare the API request
            url = f"https://api.dynamicmockups.com/v1/mockups/{template}"
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "multipart/form-data"
            }

            files = {
                "image": ("image.png", image_data, "image/png")
            }

            # Make the API request
            response = requests.post(
                url,
                headers=headers,
                files=files
            )

            if response.status_code != 200:
                print(f"Failed to generate mockup for template {template}: {response.text}")
                continue

            # Save the mockup
            output_path = self._output_dir / f"mockup_{template}.png"
            with open(output_path, "wb") as f:
                f.write(response.content)
            mockup_paths.append(str(output_path))

        if not mockup_paths:
            raise RuntimeError("Failed to generate any mockups")

        return mockup_paths 