import os
import stat
import shutil
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, List
import subprocess
import sys
import tempfile
import cv2
import traceback
import time
import json

from PIL import Image, ImageFilter, ImageEnhance


class PrintPreparationTool:
    """
    Tool for preparing images for print using Pillow for image processing.
    """

    # Standard portrait print sizes in inches at 300 DPI (height > width)
    PORTRAIT_PRINT_SIZES: Dict[str, Dict[str, int]] = {
        "4x6": {"width": 1200, "height": 1800},  # 4x6 inches at 300 DPI
        "5x7": {"width": 1500, "height": 2100},  # 5x7 inches at 300 DPI
        "8x10": {"width": 2400, "height": 3000},  # 8x10 inches at 300 DPI
        "11x14": {"width": 3300, "height": 4200},  # 11x14 inches at 300 DPI
        "16x20": {"width": 4800, "height": 6000},  # 16x20 inches at 300 DPI
    }

    # Standard landscape print sizes in inches at 300 DPI (width > height)
    LANDSCAPE_PRINT_SIZES: Dict[str, Dict[str, int]] = {
        "6x4": {"width": 1800, "height": 1200},  # 6x4 inches at 300 DPI
        "7x5": {"width": 2100, "height": 1500},  # 7x5 inches at 300 DPI
        "10x8": {"width": 3000, "height": 2400},  # 10x8 inches at 300 DPI
        "14x11": {"width": 4200, "height": 3300},  # 14x11 inches at 300 DPI
        "20x16": {"width": 6000, "height": 4800},  # 20x16 inches at 300 DPI
    }

    # Default to portrait for backward compatibility
    # PRINT_SIZES = PORTRAIT_PRINT_SIZES

    def __init__(self, realesrgan_path: Optional[str] = None):
        """
        Initialize the PrintPreparationTool.

        Args:
            realesrgan_path: Path to the Real-ESRGAN executable (if available).
                This is kept for backward compatibility but not used by default.
        """
        self.realesrgan_path = realesrgan_path
        self.output_dir = Path("output/processed_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create a temp directory for working files
        self.temp_dir = Path("output/temp")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        print("Using Pillow for image processing and upscaling")
        if realesrgan_path:
            print(f"Real-ESRGAN executable path provided: {realesrgan_path}")
            print("Will attempt to use it if available")

    def _create_temp_copy(self, image_path: str, max_retries=3) -> str:
        """
        Create a temporary copy of the image to avoid permission issues.

        Args:
            image_path: Path to the original image
            max_retries: Maximum number of retry attempts

        Returns:
            Path to the temporary copy
        """
        # Generate a unique filename with timestamp
        timestamp = int(time.time())
        temp_path = self.temp_dir / f"temp_{timestamp}_{Path(image_path).name}"

        # Try to copy the file with retries
        for attempt in range(max_retries):
            try:
                # Try direct file copy first
                shutil.copy2(image_path, temp_path)
                print(f"Successfully copied image on attempt {attempt+1}")

                # Set permissive file permissions
                os.chmod(
                    temp_path,
                    stat.S_IRUSR
                    | stat.S_IWUSR
                    | stat.S_IRGRP
                    | stat.S_IWGRP
                    | stat.S_IROTH
                    | stat.S_IWOTH,
                )

                return str(temp_path)
            except PermissionError as e:
                print(f"Permission error on attempt {attempt+1}: {e}")

                # If direct copy fails, try reading the file into memory and writing it out
                try:
                    # Wait a bit before retrying (with increasing delay)
                    time.sleep(1 + attempt)

                    # Try to open and read the image with PIL
                    img = Image.open(image_path)
                    img_copy = img.copy()  # Create a copy in memory
                    img.close()  # Close the original file

                    # Save the in-memory copy to the destination
                    img_copy.save(temp_path)

                    # Set permissive file permissions
                    os.chmod(
                        temp_path,
                        stat.S_IRUSR
                        | stat.S_IWUSR
                        | stat.S_IRGRP
                        | stat.S_IWGRP
                        | stat.S_IROTH
                        | stat.S_IWOTH,
                    )

                    print(f"Successfully copied image using PIL on attempt {attempt+1}")
                    return str(temp_path)
                except Exception as e2:
                    print(f"PIL copy failed on attempt {attempt+1}: {e2}")

                    if attempt == max_retries - 1:
                        print(f"Failed to copy image after {max_retries} attempts")
                        raise RuntimeError(f"Cannot access image file: {image_path}")

                    # Wait before next attempt
                    time.sleep(2 + attempt)

        raise RuntimeError(f"Failed to create temporary copy of {image_path}")

    def upscale_image(self, image_path: str, scale: int = 4) -> Image.Image:
        """
        Upscale an image using Pillow's high-quality resizing.

        Args:
            image_path: Path to the input image
            scale: Upscaling factor (default: 4)

        Returns:
            Upscaled PIL Image
        """
        try:
            # Create a temporary copy to avoid permission issues
            temp_image_path = self._create_temp_copy(image_path)

            # First try using Real-ESRGAN executable if path is provided
            if self.realesrgan_path and os.path.exists(self.realesrgan_path):
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_output = os.path.join(temp_dir, "upscaled.png")

                        cmd = [
                            self.realesrgan_path,
                            "-i",
                            temp_image_path,
                            "-o",
                            temp_output,
                            "-s",
                            str(scale),
                            "-n",
                            "RealESRGAN_x4plus",  # Default model
                        ]

                        print(f"Running Real-ESRGAN with command: {' '.join(cmd)}")
                        result = subprocess.run(
                            cmd, check=True, capture_output=True, text=True
                        )
                        print(f"Real-ESRGAN output: {result.stdout}")

                        if os.path.exists(temp_output):
                            print("Real-ESRGAN upscaling successful")
                            upscaled_img = Image.open(temp_output)
                            upscaled_copy = upscaled_img.copy()
                            upscaled_img.close()
                            return upscaled_copy
                except Exception as e:
                    print(f"Real-ESRGAN executable failed: {str(e)}")
                    print("Falling back to Pillow")

            # Load the image with Pillow
            print(f"Loading image: {temp_image_path}")
            img = Image.open(temp_image_path)

            # Get original dimensions
            orig_width, orig_height = img.size
            new_width, new_height = orig_width * scale, orig_height * scale

            print(
                f"Upscaling from {orig_width}x{orig_height} to {new_width}x{new_height}"
            )

            # Use high-quality upscaling with Pillow
            # First convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Use LANCZOS resampling for high-quality upscaling
            upscaled = img.resize((new_width, new_height), Image.LANCZOS)

            # Apply some enhancements to improve quality
            # Slightly sharpen the image
            upscaled = upscaled.filter(ImageFilter.SHARPEN)

            # Enhance contrast slightly
            enhancer = ImageEnhance.Contrast(upscaled)
            upscaled = enhancer.enhance(1.1)

            # Enhance color slightly
            enhancer = ImageEnhance.Color(upscaled)
            upscaled = enhancer.enhance(1.05)

            # Close the original image
            img.close()

            # Clean up the temporary file
            try:
                os.remove(temp_image_path)
                print(f"Removed temporary file: {temp_image_path}")
            except Exception as e:
                print(f"Warning: Failed to remove temporary file: {e}")

            print("Pillow upscaling completed successfully")
            return upscaled

        except Exception as e:
            print(f"Error upscaling image: {str(e)}")
            print("Detailed traceback:")
            traceback.print_exc()

            # Basic fallback - create a new image if all else fails
            try:
                print("Creating a fallback image...")
                # Create a simple colored image as fallback
                fallback_img = Image.new("RGB", (1024, 1024), color=(200, 200, 255))
                draw = ImageDraw.Draw(fallback_img)
                draw.text((512, 512), "Fallback Image", fill=(0, 0, 0))
                return fallback_img
            except Exception as fallback_error:
                print(f"Even fallback image creation failed: {str(fallback_error)}")
                raise RuntimeError("Cannot create any image for processing")

    def prepare_print_canvas(
        self, size_name: str, aspect_ratio: str = None
    ) -> Image.Image:
        """
        Create a blank canvas for the specified print size.

        Args:
            size_name: Name of the print size (e.g., "4x6", "8x10")
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            A blank white canvas image
        """
        print_sizes = self.get_print_sizes_for_aspect_ratio(aspect_ratio)

        if size_name not in print_sizes:
            raise ValueError(f"Invalid print size: {size_name}")

        dimensions = print_sizes[size_name]
        width = dimensions["width"]
        height = dimensions["height"]

        # Create a new white image
        canvas = Image.new("RGB", (width, height), (255, 255, 255))
        return canvas

    def center_image_on_canvas(
        self, image: Image.Image, canvas: Image.Image, fill_canvas: bool = True
    ) -> Image.Image:
        """
        Center an image on a canvas, with option to fill the canvas.

        Args:
            image: The image to center
            canvas: The canvas to center the image on
            fill_canvas: If True, image will be scaled to fill the canvas while maintaining aspect ratio.
                         If False, image will be centered with white borders.

        Returns:
            A new image with the input image centered on the canvas
        """
        # Create a copy of the canvas
        result = canvas.copy()

        # Create a copy of the image to avoid modifying the original
        image_copy = image.copy()

        if fill_canvas:
            # Calculate the aspect ratios
            canvas_aspect = canvas.width / canvas.height
            image_aspect = image_copy.width / image_copy.height

            # Determine how to resize the image to fill the canvas
            if image_aspect > canvas_aspect:
                # Image is wider than canvas (relative to height)
                # Scale to match canvas height and crop width
                scale_factor = canvas.height / image_copy.height
                new_width = int(image_copy.width * scale_factor)
                new_height = canvas.height

                # Resize the image to the new dimensions
                image_copy = image_copy.resize((new_width, new_height), Image.LANCZOS)

                # Calculate crop box to center the image horizontally
                left = (new_width - canvas.width) // 2
                right = left + canvas.width
                crop_box = (left, 0, right, new_height)

                # Crop the image
                image_copy = image_copy.crop(crop_box)
            else:
                # Image is taller than canvas (relative to width)
                # Scale to match canvas width and crop height
                scale_factor = canvas.width / image_copy.width
                new_width = canvas.width
                new_height = int(image_copy.height * scale_factor)

                # Resize the image to the new dimensions
                image_copy = image_copy.resize((new_width, new_height), Image.LANCZOS)

                # Calculate crop box to center the image vertically
                top = (new_height - canvas.height) // 2
                bottom = top + canvas.height
                crop_box = (0, top, new_width, bottom)

                # Crop the image
                image_copy = image_copy.crop(crop_box)

            # Ensure the image exactly matches the canvas dimensions
            if image_copy.width != canvas.width or image_copy.height != canvas.height:
                image_copy = image_copy.resize(
                    (canvas.width, canvas.height), Image.LANCZOS
                )

            # Paste the resized and cropped image onto the canvas
            result.paste(image_copy, (0, 0))
        else:
            # Original behavior: resize to fit within canvas and center with white borders
            # Resize the image to fit within the canvas while maintaining aspect ratio
            image_copy.thumbnail((canvas.width, canvas.height), Image.LANCZOS)

            # Calculate the position to center the image
            x = (canvas.width - image_copy.width) // 2
            y = (canvas.height - image_copy.height) // 2

            # Paste the image onto the canvas
            result.paste(image_copy, (x, y))

        return result

    def prepare_image_for_print(
        self,
        image_path: str,
        size_name: str,
        output_filename: Optional[str] = None,
        fill_canvas: bool = True,
        aspect_ratio: str = None,
    ) -> str:
        """
        Prepare an image for print by upscaling and centering on a canvas.

        Args:
            image_path: Path to the input image
            size_name: Name of the print size (e.g., "4x6", "8x10")
            output_filename: Optional name for the output file
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            Path to the prepared image
        """
        try:
            print(
                f"Preparing image for print: {image_path} at size {size_name} with aspect ratio {aspect_ratio}"
            )

            # Upscale the image
            upscaled_img = self.upscale_image(image_path)

            # Create a canvas for the specified print size
            canvas = self.prepare_print_canvas(size_name, aspect_ratio)

            # Center the upscaled image on the canvas
            result = self.center_image_on_canvas(
                upscaled_img, canvas, fill_canvas=fill_canvas
            )

            # Set the DPI metadata
            result.info["dpi"] = (300, 300)

            # Save the result
            if output_filename is None:
                fill_indicator = "filled" if fill_canvas else "centered"
                aspect_suffix = f"_{aspect_ratio}" if aspect_ratio else ""
                output_filename = f"print_ready_{Path(image_path).stem}_{size_name.replace('x', '_')}{aspect_suffix}_{fill_indicator}.png"

            output_path = self.output_dir / output_filename
            result.save(output_path, dpi=(300, 300))

            print(f"✓ Image prepared for print: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"Error preparing image for print: {str(e)}")
            traceback.print_exc()
            raise

    def prepare_all_print_sizes(
        self, image_path: str, fill_canvas: bool = True, aspect_ratio: str = None
    ) -> List[str]:
        """
        Prepare an image for all standard print sizes.

        Args:
            image_path: Path to the input image
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            List of paths to the prepared images
        """
        output_paths = []

        # Get the appropriate print sizes based on aspect ratio
        print_sizes = self.get_print_sizes_for_aspect_ratio(aspect_ratio)

        for size_name in print_sizes.keys():
            try:
                output_path = self.prepare_image_for_print(
                    image_path,
                    size_name,
                    fill_canvas=fill_canvas,
                    aspect_ratio=aspect_ratio,
                )
                output_paths.append(output_path)
            except Exception as e:
                print(f"Error preparing image for size {size_name}: {str(e)}")
                continue

        return output_paths

    def get_print_sizes_for_aspect_ratio(
        self, aspect_ratio: str = None
    ) -> Dict[str, Dict[str, int]]:
        """
        Get the appropriate print sizes dictionary based on the aspect ratio.

        Args:
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            Dictionary of print sizes appropriate for the specified aspect ratio
        """
        if aspect_ratio == "landscape":
            print("Using landscape print sizes")
            return self.LANDSCAPE_PRINT_SIZES
        else:
            # Default to portrait for backward compatibility or if explicitly specified
            print(f"Using portrait print sizes (aspect_ratio={aspect_ratio})")
            return self.PORTRAIT_PRINT_SIZES

    def run(self, input_str: str) -> str:
        """
        Run the tool with the provided input.

        Args:
            input_str: Either a direct image path or a JSON string with parameters
                       including 'image_path' and optionally 'aspect_ratio' and 'fill_canvas'

        Returns:
            A string containing the paths to the processed images
        """
        try:
            # Check if input is JSON
            try:
                input_data = json.loads(input_str)
                if isinstance(input_data, dict):
                    image_path = input_data.get("image_path", "")
                    aspect_ratio = input_data.get("aspect_ratio", None)
                    fill_canvas = input_data.get("fill_canvas", True)

                    if not image_path:
                        return (
                            "Error: Missing required field 'image_path' in JSON input"
                        )

                    print(
                        f"Processing image with aspect_ratio={aspect_ratio}, fill_canvas={fill_canvas}"
                    )
                    output_paths = self.prepare_all_print_sizes(
                        image_path, fill_canvas=fill_canvas, aspect_ratio=aspect_ratio
                    )
                    return json.dumps(output_paths)
            except json.JSONDecodeError:
                # Not JSON, treat as direct image path
                print("Input is not JSON, treating as direct image path")
                output_paths = self.prepare_all_print_sizes(input_str)
                return json.dumps(output_paths)

        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return error_msg
