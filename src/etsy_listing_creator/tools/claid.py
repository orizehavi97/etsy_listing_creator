import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from PIL import Image
from pydantic import Field, PrivateAttr
import base64

from crewai.tools import BaseTool
from .print_prep import PrintPreparationTool


class ClaidImageTool(BaseTool):
    name: str = "Claid Image Processor"
    description: str = """
    Process images to meet print quality standards using either Claid.ai API or local processing with Real-ESRGAN.
    Input should be a path to an image file.
    Returns a list of paths to the processed image files in different sizes.
    """

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()
    _imgbb_key: str = PrivateAttr()
    _output_dir: Path = PrivateAttr()
    _base_url: str = PrivateAttr(default="https://api.claid.ai")
    _use_local_processing: bool = PrivateAttr(default=False)
    _print_prep_tool: PrintPreparationTool = PrivateAttr()

    # Standard print sizes in inches at 300 DPI
    _print_sizes: Dict[str, Dict[str, int]] = PrivateAttr(
        default={
            "4x6": {"width": 1200, "height": 1800},  # 4x6 inches at 300 DPI
            "5x7": {"width": 1500, "height": 2100},  # 5x7 inches at 300 DPI
            "8x10": {"width": 2400, "height": 3000},  # 8x10 inches at 300 DPI
            "11x14": {"width": 3300, "height": 4200},  # 11x14 inches at 300 DPI
            "16x20": {"width": 4800, "height": 6000},  # 16x20 inches at 300 DPI
        }
    )

    def __init__(
        self, use_local_processing: bool = True, realesrgan_path: str = None, **kwargs
    ):
        super().__init__(**kwargs)
        # Set up API key
        self._api_key = os.getenv("CLAID_API_KEY")
        self._imgbb_key = os.getenv("IMGBB_API_KEY")

        # Set up output directory
        self._output_dir = Path("output/processed_images")
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Set up local processing option
        self._use_local_processing = use_local_processing
        if use_local_processing:
            self._print_prep_tool = PrintPreparationTool(
                realesrgan_path=realesrgan_path
            )
            print("Using local processing with PrintPreparationTool")
        else:
            print(
                "WARNING: Using Claid.ai API for image processing. This will consume API credits."
            )
            print(
                "Consider using local processing instead by setting use_local_processing=True"
            )
            if not self._api_key:
                raise ValueError(
                    "CLAID_API_KEY environment variable is required when use_local_processing=False"
                )

    def _get_headers(self) -> Dict[str, str]:
        """Get required headers for API requests"""
        return {
            "Host": "api.claid.ai",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _create_temp_copy(self, image_path: str) -> str:
        """
        Create a temporary copy of the image to avoid permission issues.

        Args:
            image_path: Path to the original image

        Returns:
            Path to the temporary copy
        """
        # Create a temporary directory if it doesn't exist
        temp_dir = Path("output/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Create a temporary file name
        temp_path = temp_dir / f"temp_{Path(image_path).name}"

        # Copy the file
        try:
            shutil.copy2(image_path, temp_path)
            print(f"Created temporary copy at: {temp_path}")
            return str(temp_path)
        except Exception as e:
            print(f"Error creating temporary copy: {e}")
            # If copy fails, try creating a new file
            try:
                with open(image_path, "rb") as src:
                    with open(temp_path, "wb") as dst:
                        dst.write(src.read())
                print(f"Created temporary copy using file read/write: {temp_path}")
                return str(temp_path)
            except Exception as e2:
                print(f"Failed to create temporary copy: {e2}")
                raise RuntimeError(f"Cannot access image file: {image_path}")

    def _upload_to_imgbb(self, image_path: str) -> str:
        """
        Upload an image to ImgBB and get a public URL.

        Args:
            image_path: Path to the image file to upload

        Returns:
            Public URL of the uploaded image
        """
        upload_url = "https://api.imgbb.com/1/upload"

        # Create a temporary copy to avoid permission issues
        temp_image_path = self._create_temp_copy(image_path)

        # Verify the image exists and API key is set
        if not os.path.exists(temp_image_path):
            raise ValueError(f"Image file not found: {temp_image_path}")

        if not self._imgbb_key:
            raise ValueError("IMGBB_API_KEY environment variable is required")

        try:
            # Prepare the file for upload
            with open(temp_image_path, "rb") as img_file:
                # ImgBB expects the image as base64
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            # Make the request
            print(f"Uploading image to ImgBB: {temp_image_path}")
            response = requests.post(
                upload_url,
                data={
                    "key": self._imgbb_key,
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
        finally:
            # Clean up the temporary file
            try:
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                    print(f"Removed temporary file: {temp_image_path}")
            except Exception as e:
                print(f"Warning: Failed to remove temporary file: {e}")

    def _run_with_data(
        self, image_path: str, data: Dict, size_name: str, fill_canvas: bool = True
    ) -> str:
        """
        Process an image with custom data for a specific print size.

        Args:
            image_path: Path to the input image
            data: Custom processing parameters
            size_name: Name of the print size (e.g., "4x6", "8x10")
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.

        Returns:
            Path to the processed image
        """
        if self._use_local_processing:
            # Use local processing with PrintPreparationTool
            print(f"Using local processing for size: {size_name}")
            return self._print_prep_tool.prepare_image_for_print(
                image_path,
                size_name,
                f"claid_processed_{Path(image_path).stem}_{size_name.replace('x', '_')}.png",
                fill_canvas=fill_canvas,
            )

        # Create a temporary copy to avoid permission issues
        temp_image_path = self._create_temp_copy(image_path)

        # Upload the image to get a URL for Claid API
        image_url = self._upload_to_imgbb(temp_image_path)

        # Prepare the request data
        request_data = {
            "asset": image_url,
            "params": data,
        }

        # Add size-specific dimensions
        if size_name in self._print_sizes:
            dimensions = self._print_sizes[size_name]
            request_data["params"]["width"] = dimensions["width"]
            request_data["params"]["height"] = dimensions["height"]

        # Make the request
        print(f"Processing image with Claid API for size: {size_name}")
        print(f"Request data: {json.dumps(request_data, indent=2)}")

        response = requests.post(
            f"{self._base_url}/v1/image/enhance",
            headers=self._get_headers(),
            json=request_data,
            timeout=60,  # Increased timeout for larger images
        )

        # Check response
        if response.status_code != 200:
            print(f"Processing failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            raise RuntimeError(f"Failed to process image: {response.text}")

        # Parse response
        result = response.json()
        if "url" not in result:
            print(f"Processing failed: {result}")
            raise RuntimeError("Processing failed")

        # Download the processed image
        processed_url = result["url"]
        print(f"Processed image URL: {processed_url}")

        # Save the processed image
        output_filename = (
            f"claid_processed_{Path(image_path).stem}_{size_name.replace('x', '_')}.png"
        )
        output_path = self._output_dir / output_filename

        # Download the processed image
        img_response = requests.get(processed_url, timeout=30)
        if img_response.status_code != 200:
            raise RuntimeError(
                f"Failed to download processed image: {img_response.status_code}"
            )

        with open(output_path, "wb") as f:
            f.write(img_response.content)

        print(f"✓ Processed image saved to: {output_path}")
        return str(output_path)

    def _run(self, image_path: str, fill_canvas: bool = True) -> List[str]:
        """
        Process an image for all standard print sizes.

        Args:
            image_path: Path to the input image
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.

        Returns:
            List of paths to the processed images
        """
        # Default processing parameters
        default_params = {
            "smart_enhance": True,
            "hdr": 100,
            "quality": 85,
        }

        output_paths = []
        for size_name in self._print_sizes.keys():
            try:
                output_path = self._run_with_data(
                    image_path, default_params, size_name, fill_canvas=fill_canvas
                )
                output_paths.append(output_path)
            except Exception as e:
                print(f"Error processing image for size {size_name}: {str(e)}")
                continue

        return output_paths
