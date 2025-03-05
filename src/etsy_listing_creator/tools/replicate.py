import os
import stat
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import replicate
import requests
from pydantic import Field, PrivateAttr
import base64

from crewai.tools import BaseTool


class ReplicateImageTool(BaseTool):
    name: str = "Replicate Image Generator"
    description: str = """
    Generate high-quality images using Replicate's API.
    Input should be a detailed prompt describing the desired image.
    Returns the path to the generated image file.
    """

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()
    _output_dir: Path = PrivateAttr()
    _model_id: str = PrivateAttr(
        default="orizehavi97/etsy-listing-creator-v1:db1218c83515c6fdaafa2e0c0fa20ec860044591bbd0a48eba827b5fd4a49439"
    )
    _default_params: Dict[str, Any] = PrivateAttr(
        default={
            "model": "dev",
            "go_fast": False,
            "lora_scale": 1,
            "megapixels": "1",
            "num_outputs": 1,
            "aspect_ratio": "1:1",
            "output_format": "webp",
            "guidance_scale": 3,
            "output_quality": 80,
            "prompt_strength": 0.8,
            "extra_lora_scale": 1,
            "num_inference_steps": 28,
        }
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set up API key
        self._api_key = os.getenv("REPLICATE_API_TOKEN")
        if not self._api_key:
            raise ValueError("REPLICATE_API_TOKEN environment variable is required")

        # Set the API token for the replicate library
        os.environ["REPLICATE_API_TOKEN"] = self._api_key

        # Set up output directory
        self._output_dir = Path("output/images")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _run(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate an image using Replicate.

        Args:
            prompt: Detailed description of the desired image
            params: Optional parameters to override the defaults

        Returns:
            Path to the generated image file
        """
        print(f"Generating image with prompt: {prompt}")

        # Prepare input parameters
        input_params = self._default_params.copy()
        if params:
            input_params.update(params)

        # Add the prompt to the input parameters
        input_params["prompt"] = prompt

        try:
            # Run the model
            print(f"Running Replicate model: {self._model_id}")
            print(f"Input parameters: {input_params}")

            output = replicate.run(self._model_id, input=input_params)

            print(f"Replicate output: {output}")

            # The output is typically a list of image URLs
            if not output or not isinstance(output, list) or len(output) == 0:
                raise ValueError(f"Unexpected output format from Replicate: {output}")

            # Download the first image
            image_url = output[0]
            print(f"Downloading image from: {image_url}")

            # Generate a unique filename with timestamp
            timestamp = int(time.time())
            img_path = (
                self._output_dir
                / f"replicate_generated_{timestamp}.{input_params['output_format']}"
            )

            # Download the image
            response = requests.get(image_url, stream=True)
            if response.status_code != 200:
                raise RuntimeError(f"Failed to download image: {response.status_code}")

            with open(img_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Set file permissions to ensure it's readable and writable
            os.chmod(
                img_path,
                stat.S_IRUSR
                | stat.S_IWUSR
                | stat.S_IRGRP
                | stat.S_IWGRP
                | stat.S_IROTH
                | stat.S_IWOTH,
            )

            print(f"✓ Image generated and saved to: {img_path}")
            return str(img_path)

        except Exception as e:
            print(f"Error generating image with Replicate: {str(e)}")
            raise RuntimeError(f"Failed to generate image: {str(e)}")

    def upload_image(self, image_path: str) -> str:
        """
        Upload an image to ImgBB and get a public URL.

        Args:
            image_path: Path to the image file to upload

        Returns:
            Public URL of the uploaded image
        """
        upload_url = "https://api.imgbb.com/1/upload"

        # Verify the image exists
        if not os.path.exists(image_path):
            raise ValueError(f"Image file not found: {image_path}")

        imgbb_key = os.getenv("IMGBB_API_KEY")
        if not imgbb_key:
            raise ValueError(
                "IMGBB_API_KEY environment variable is required for image uploading"
            )

        try:
            # Prepare the file for upload
            with open(image_path, "rb") as img_file:
                # ImgBB expects the image as base64
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            # Make the request
            print(f"Uploading image: {image_path}")
            response = requests.post(
                upload_url,
                data={
                    "key": imgbb_key,
                    "image": image_data,
                },
                timeout=30,
            )

            # Check response
            if response.status_code != 200:
                print(f"Upload failed with status code: {response.status_code}")
                print(f"Response: {response.text}")
                raise RuntimeError(f"Failed to upload image: {response.text}")

            # Parse response
            result = response.json()
            if not result.get("success"):
                print(f"Upload failed: {result}")
                raise RuntimeError("Upload failed")

            # Get the URL - ImgBB provides several URLs, we'll use the direct display URL
            url = result["data"]["display_url"]
            print(f"✓ Image uploaded successfully to: {url}")
            return url

        except Exception as e:
            print(f"Error uploading image: {str(e)}")
            raise RuntimeError(f"Failed to upload image: {str(e)}")

    def generate_and_upload(
        self, prompt: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Generate an image and upload it to ImgBB.

        Args:
            prompt: Detailed description of the desired image
            params: Optional parameters to override the defaults

        Returns:
            Tuple of (local_path, public_url)
        """
        # Generate the image
        local_path = self._run(prompt, params)

        # Upload the image
        public_url = self.upload_image(local_path)

        return local_path, public_url

    def run(self, tool_input: str) -> str:
        """
        Run the tool with the given input.

        Args:
            tool_input: Input to the tool, can be a simple prompt or a JSON string with
                       additional parameters

        Returns:
            Path to the generated image file
        """
        try:
            # Check if the input is a JSON string with additional parameters
            try:
                import json

                input_data = json.loads(tool_input)
                if isinstance(input_data, dict):
                    prompt = input_data.pop("prompt", "")
                    if not prompt:
                        return "Error: 'prompt' is required in the JSON input"

                    return self._run(prompt, input_data)
            except (json.JSONDecodeError, TypeError):
                # If it's not valid JSON, treat it as a simple prompt
                pass

            # Simple prompt input
            return self._run(tool_input)
        except Exception as e:
            return f"Error: {str(e)}"
