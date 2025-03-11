import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
import stat
import requests
import json
import shutil
import base64
import builtins

from pydantic import Field, PrivateAttr
from crewai.tools import BaseTool

import replicate


class ReplicateTool(BaseTool):
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
            "aspect_ratio": "1:1",  # Default square aspect ratio
            "output_format": "webp",
            "guidance_scale": 3,
            "output_quality": 80,
            "prompt_strength": 0.8,
            "extra_lora_scale": 1,
            "num_inference_steps": 28,
        }
    )

    # Mapping of aspect ratio names to API values
    _aspect_ratio_mapping: Dict[str, str] = PrivateAttr(
        default={"portrait": "2:3", "landscape": "3:2", None: "1:1"}  # Default square
    )

    def __init__(self, model_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        # Set up the API key
        self._api_key = os.getenv("REPLICATE_API_TOKEN")
        if not self._api_key:
            raise ValueError("REPLICATE_API_TOKEN environment variable is required")

        # Set the model ID if provided
        if model_id:
            self._model_id = model_id

        # Set up output directory
        self._output_dir = Path("output/images")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _run(self, prompt: str, aspect_ratio: str = None) -> str:
        """
        Generate an image using Replicate and ask for user approval.

        Args:
            prompt: Detailed description of the desired image
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default square)

        Returns:
            Path to the generated image file
        """
        print(f"Generating image with prompt: {prompt}")
        print(f"Using aspect ratio: {aspect_ratio or 'default (1:1)'}")

        # Generate the image
        image_path = self._generate_image(prompt, aspect_ratio)
        
        # Ask for user approval
        print("\n===== IMAGE APPROVAL REQUIRED =====")
        print(f"An image has been generated and saved to: {image_path}")
        print("Please review the image and decide if you want to proceed with it.")
        
        while True:
            user_response = input("Do you approve this image? (yes/no): ").strip().lower()
            
            if user_response in ["yes", "y"]:
                print("Image approved! Continuing with the workflow.")
                return image_path
            elif user_response in ["no", "n"]:
                print("Image rejected. Generating a new image...")
                
                # Delete the rejected image
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        print(f"Deleted rejected image: {image_path}")
                except Exception as e:
                    print(f"Warning: Could not delete rejected image: {str(e)}")
                
                # Generate a new image
                image_path = self._generate_image(prompt, aspect_ratio)
            else:
                print("Invalid response. Please enter 'yes' or 'no'.")

    def _generate_image(self, prompt: str, aspect_ratio: str = None) -> str:
        """
        Internal method to generate an image using Replicate.

        Args:
            prompt: Detailed description of the desired image
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default square)

        Returns:
            Path to the generated image file
        """
        # Prepare the input parameters
        input_params = self._default_params.copy()
        input_params["prompt"] = prompt

        # Set the aspect ratio if provided
        if aspect_ratio:
            api_aspect_ratio = self._aspect_ratio_mapping.get(aspect_ratio)
            if api_aspect_ratio:
                input_params["aspect_ratio"] = api_aspect_ratio
                print(f"Setting aspect ratio to: {api_aspect_ratio}")

        try:
            # Generate the image
            print(f"Calling Replicate API with model: {self._model_id}")
            output = replicate.run(self._model_id, input=input_params)

            # The output can be a list of URLs, a string URL, or a FileOutput object
            print(f"Output type: {type(output)}")
            print(f"Output content: {output}")

            # Handle different output types
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
                print(f"Image generated successfully. URL from list: {image_url}")
                return self._download_image(image_url)
            elif isinstance(output, str) and (
                output.startswith("http://") or output.startswith("https://")
            ):
                # If it's a direct URL string
                print(f"Image generated successfully. Direct URL: {output}")
                return self._download_image(output)
            elif hasattr(output, "url"):
                # If it's a FileOutput object with a url attribute
                image_url = output.url
                print(f"Image generated successfully. URL from object: {image_url}")
                return self._download_image(image_url)
            elif hasattr(output, "download"):
                # If it's a FileOutput object with a download method
                print("Output has download method, using it directly")
                # Generate a unique filename with timestamp
                timestamp = int(time.time())
                img_path = self._output_dir / f"replicate_generated_{timestamp}.webp"

                # Download the file directly
                output.download(str(img_path))

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

                print(f"✓ Image downloaded and saved to: {img_path}")
                return str(img_path)
            else:
                raise ValueError(f"Unexpected output format from Replicate: {output}")

        except Exception as e:
            print(f"Error generating image: {str(e)}")
            raise RuntimeError(f"Failed to generate image: {str(e)}")

    def _download_image(self, image_url: str) -> str:
        """
        Download an image from a URL and save it locally.

        Args:
            image_url: URL of the image to download

        Returns:
            Path to the downloaded image file
        """
        try:
            # Generate a unique filename with timestamp
            timestamp = int(time.time())

            # Try to extract file extension from URL
            try:
                file_extension = image_url.split(".")[-1]
                if "?" in file_extension:  # Handle URLs with query parameters
                    file_extension = file_extension.split("?")[0]
                if not file_extension or len(file_extension) > 5:
                    file_extension = (
                        "webp"  # Default to webp if extension can't be determined
                    )
            except (AttributeError, IndexError):
                # If URL doesn't have a proper extension or isn't a string
                file_extension = "webp"

            img_path = (
                self._output_dir / f"replicate_generated_{timestamp}.{file_extension}"
            )

            # Download the image
            print(f"Downloading image from {image_url}")
            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()

            # Save the image
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

            print(f"✓ Image downloaded and saved to: {img_path}")
            return str(img_path)

        except Exception as e:
            print(f"Error downloading image: {str(e)}")

            # Fallback: try to save with a default name if there was an issue with the URL
            try:
                timestamp = int(time.time())
                img_path = self._output_dir / f"replicate_generated_{timestamp}.webp"

                print(f"Trying alternative download approach for: {image_url}")
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()

                with open(img_path, "wb") as f:
                    f.write(response.content)

                os.chmod(
                    img_path,
                    stat.S_IRUSR
                    | stat.S_IWUSR
                    | stat.S_IRGRP
                    | stat.S_IWGRP
                    | stat.S_IROTH
                    | stat.S_IWOTH,
                )

                print(f"✓ Image downloaded and saved to: {img_path} (fallback method)")
                return str(img_path)
            except Exception as e2:
                print(f"Error in fallback download: {str(e2)}")
                raise RuntimeError(f"Failed to download image: {str(e)}")

    def generate_and_upload(
        self, prompt: str, aspect_ratio: str = None
    ) -> tuple[str, str]:
        """
        Generate an image and upload it to ImgBB.

        Args:
            prompt: Detailed description of the desired image
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default square)

        Returns:
            Tuple of (local_path, image_url)
        """
        local_path = ""
        image_url = ""

        # Step 1: Generate the image
        try:
            local_path = self._run(prompt, aspect_ratio)
            if not local_path or not os.path.exists(local_path):
                print("Warning: Generated image path is invalid or file doesn't exist")
                return "", ""

            print(f"Successfully generated image at: {local_path}")
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return "", ""

        # Step 2: Upload to ImgBB (if needed)
        try:
            from .image_processing import ImageProcessingTool

            # Create a temporary copy of the image
            temp_dir = Path("output/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"temp_{Path(local_path).name}"
            shutil.copy2(local_path, temp_path)

            # Upload to ImgBB
            imgbb_key = os.getenv("IMGBB_API_KEY")
            if imgbb_key:
                with open(temp_path, "rb") as file:
                    image_data = base64.b64encode(file.read()).decode("utf-8")
                
                url = "https://api.imgbb.com/1/upload"
                payload = {
                    "key": imgbb_key,
                    "image": image_data,
                }
                
                response = requests.post(url, payload)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", False):
                        image_url = result["data"]["url"]
                        print(f"✓ Image uploaded to ImgBB: {image_url}")
                    else:
                        print(f"Warning: ImgBB upload failed: {result.get('error', {}).get('message', 'Unknown error')}")
                        image_url = ""
                else:
                    print(f"Warning: ImgBB upload failed with status code {response.status_code}")
                    image_url = ""
            else:
                print("Warning: IMGBB_API_KEY not found in environment variables")
                image_url = ""
        except Exception as e:
            print(f"Warning: Failed to upload image to ImgBB: {str(e)}")
            print("Returning local path only")
            image_url = ""

        return local_path, image_url

    def run(self, input_str: str) -> str:
        """
        Run the tool with the provided input.

        Args:
            input_str: Either a direct prompt string or a JSON string with parameters
                       including 'prompt' and optionally 'aspect_ratio'

        Returns:
            JSON string containing the path to the generated image and the aspect ratio used
        """
        try:
            # Check if input is JSON
            try:
                input_data = json.loads(input_str)
                if isinstance(input_data, dict):
                    prompt = input_data.get("prompt", "")
                    aspect_ratio = input_data.get("aspect_ratio", None)

                    if not prompt:
                        return "Error: Missing required field 'prompt' in JSON input"

                    image_path = self._run(prompt, aspect_ratio)

                    # Return a JSON object with both the image path and aspect ratio
                    result = {"image_path": image_path, "aspect_ratio": aspect_ratio}
                    return json.dumps(result)
            except json.JSONDecodeError:
                # Not JSON, treat as direct prompt
                image_path = self._run(input_str)

                # Return a JSON object with just the image path
                result = {"image_path": image_path, "aspect_ratio": None}
                return json.dumps(result)

        except Exception as e:
            return f"Error: {str(e)}"
