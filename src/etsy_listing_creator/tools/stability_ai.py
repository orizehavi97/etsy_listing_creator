import os
from pathlib import Path
from typing import List

import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from stability_sdk import client
from pydantic import Field, PrivateAttr
import requests

from crewai.tools import BaseTool

class StabilityAITool(BaseTool):
    name: str = "Stability AI Image Generator"
    description: str = """
    Generate high-quality images using Stability AI's API.
    Input should be a detailed prompt describing the desired image.
    Returns the path to the generated image file.
    """

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()
    _output_dir: Path = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set up the host and API key
        os.environ['STABILITY_HOST'] = 'grpc.stability.ai:443'
        self._api_key = os.getenv("STABILITY_KEY")
        if not self._api_key:
            raise ValueError("STABILITY_KEY environment variable is required")
        
        self._output_dir = Path("output/images")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _run(self, prompt: str) -> str:
        """
        Generate an image using Stability AI.
        
        Args:
            prompt: Detailed description of the desired image
            
        Returns:
            Path to the generated image file
        """
        # Initialize Stability client
        stability_api = client.StabilityInference(
            key=self._api_key,
            host=os.getenv('STABILITY_HOST', 'grpc.stability.ai:443'),
            verbose=True,
        )

        # Generate the image
        answers = stability_api.generate(
            prompt=prompt,
            seed=42,  # Optional: for reproducibility
            steps=50,  # Number of diffusion steps
            cfg_scale=8.0,  # How strictly to follow the prompt
            width=1024,  # Image width
            height=1024,  # Image height
            samples=1,  # Number of images to generate
            sampler=generation.SAMPLER_K_DPMPP_2M  # Sampling method
        )

        # Process the response
        for resp in answers:
            for artifact in resp.artifacts:
                if artifact.finish_reason == generation.FILTER:
                    raise ValueError(
                        "Your request activated the API's safety filters and could not be processed."
                        "Please modify the prompt and try again."
                    )
                
                if artifact.type == generation.ARTIFACT_IMAGE:
                    img_path = self._output_dir / f"generated_{artifact.seed}.png"
                    with open(img_path, "wb") as f:
                        f.write(artifact.binary)
                    return str(img_path)

        raise RuntimeError("Failed to generate image")

    def upload_image(self, image_path: str) -> str:
        """
        Upload an image to ImgBB and get a public URL.
        
        Args:
            image_path: Path to the image file to upload
            
        Returns:
            Public URL of the uploaded image
        """
        upload_url = "https://api.imgbb.com/1/upload"
        
        # Verify the image exists and API key is set
        if not os.path.exists(image_path):
            raise ValueError(f"Image file not found: {image_path}")
        
        imgbb_key = os.getenv("IMGBB_API_KEY")
        if not imgbb_key:
            raise ValueError("IMGBB_API_KEY environment variable is required")
        
        try:
            # Prepare the file for upload
            with open(image_path, 'rb') as img_file:
                # ImgBB expects the image as base64
                import base64
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Make the request
            print(f"Uploading image: {image_path}")
            response = requests.post(
                upload_url,
                data={
                    'key': imgbb_key,
                    'image': image_data,
                },
                timeout=30
            )
            
            # Check response
            if response.status_code != 200:
                print(f"Upload failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                raise RuntimeError(f"Failed to upload image: {response.text}")
            
            # Parse response
            result = response.json()
            if not result.get('success'):
                print(f"Upload failed: {result}")
                raise RuntimeError("Upload failed")
            
            # Get the URL - ImgBB provides several URLs, we'll use the direct display URL
            url = result['data']['display_url']
            print(f"✓ Image uploaded successfully to: {url}")
            return url
            
        except Exception as e:
            print(f"Error uploading image: {str(e)}")
            raise RuntimeError(f"Failed to upload image: {str(e)}")

    def generate_and_upload(self, prompt: str) -> tuple[str, str]:
        """
        Generate an image and upload it to get a public URL.
        
        Args:
            prompt: Detailed description of the desired image
            
        Returns:
            Tuple of (local_path, public_url)
        """
        # Generate the image
        local_path = self._run(prompt)
        
        # Upload and get public URL
        public_url = self.upload_image(local_path)
        
        return local_path, public_url 