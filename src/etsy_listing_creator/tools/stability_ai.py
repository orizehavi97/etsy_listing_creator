import os
from pathlib import Path
from typing import List

import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from stability_sdk import client
from pydantic import Field, PrivateAttr

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