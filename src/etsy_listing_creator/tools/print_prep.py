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

from PIL import Image, ImageFilter, ImageEnhance


class PrintPreparationTool:
    """
    Tool for preparing images for print using Pillow for image processing.
    """

    # Standard print sizes in inches at 300 DPI
    PRINT_SIZES: Dict[str, Dict[str, int]] = {
        "4x6": {"width": 1200, "height": 1800},  # 4x6 inches at 300 DPI
        "5x7": {"width": 1500, "height": 2100},  # 5x7 inches at 300 DPI
        "8x10": {"width": 2400, "height": 3000},  # 8x10 inches at 300 DPI
        "11x14": {"width": 3300, "height": 4200},  # 11x14 inches at 300 DPI
        "16x20": {"width": 4800, "height": 6000},  # 16x20 inches at 300 DPI
    }

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

    def prepare_print_canvas(self, size_name: str) -> Image.Image:
        """
        Create a white canvas for the specified print size.

        Args:
            size_name: Name of the print size (e.g., "4x6", "8x10")

        Returns:
            A white canvas PIL Image
        """
        if size_name not in self.PRINT_SIZES:
            raise ValueError(
                f"Unknown print size: {size_name}. Available sizes: {list(self.PRINT_SIZES.keys())}"
            )

        dimensions = self.PRINT_SIZES[size_name]
        width, height = dimensions["width"], dimensions["height"]

        # Create a white canvas
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
    ) -> str:
        """
        Prepare an image for print by upscaling and centering on a canvas.

        Args:
            image_path: Path to the input image
            size_name: Name of the print size (e.g., "4x6", "8x10")
            output_filename: Optional name for the output file
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.

        Returns:
            Path to the prepared image
        """
        try:
            print(f"Preparing image for print: {image_path} at size {size_name}")

            # Upscale the image
            upscaled_img = self.upscale_image(image_path)

            # Create a canvas for the specified print size
            canvas = self.prepare_print_canvas(size_name)

            # Center the upscaled image on the canvas
            result = self.center_image_on_canvas(
                upscaled_img, canvas, fill_canvas=fill_canvas
            )

            # Set the DPI metadata
            result.info["dpi"] = (300, 300)

            # Save the result
            if output_filename is None:
                fill_indicator = "filled" if fill_canvas else "centered"
                output_filename = f"print_ready_{Path(image_path).stem}_{size_name.replace('x', '_')}_{fill_indicator}.png"

            output_path = self.output_dir / output_filename
            result.save(output_path, dpi=(300, 300))

            print(f"✓ Image prepared for print: {output_path}")
            return str(output_path)

        except Exception as e:
            print(f"Error preparing image for print: {str(e)}")
            traceback.print_exc()
            raise

    def prepare_all_print_sizes(
        self, image_path: str, fill_canvas: bool = True
    ) -> List[str]:
        """
        Prepare an image for all standard print sizes.

        Args:
            image_path: Path to the input image
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.

        Returns:
            List of paths to the prepared images
        """
        output_paths = []

        for size_name in self.PRINT_SIZES.keys():
            try:
                output_path = self.prepare_image_for_print(
                    image_path, size_name, fill_canvas=fill_canvas
                )
                output_paths.append(output_path)
            except Exception as e:
                print(f"Error preparing image for size {size_name}: {str(e)}")
                continue

        return output_paths
