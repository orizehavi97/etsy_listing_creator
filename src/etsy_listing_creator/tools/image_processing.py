import os
import stat
import shutil
import numpy as np
import json
import traceback
import time
import tempfile
import cv2
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Union, Any

from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont
from crewai.tools import BaseTool
from pydantic import Field, PrivateAttr


class ImageProcessingTool(BaseTool):
    """
    Tool for processing images to meet print quality standards.
    
    This tool handles:
    1. Upscaling images to high resolution
    2. Creating print-ready versions in standard sizes
    3. Enhancing image quality for printing
    4. Maintaining proper aspect ratios
    
    Input can be either a direct image path or a JSON string with parameters
    including 'image_path' and optionally 'aspect_ratio' and 'fill_canvas'.
    
    Returns a list of paths to the processed image files in different sizes.
    """
    
    name: str = "Image Processing Tool"
    description: str = """
    Process images to meet print quality standards using advanced image processing techniques.
    Input should be a path to an image file or a JSON with image_path and aspect_ratio.
    Returns a list of paths to the processed image files in different sizes.
    """

    # Private attributes using Pydantic's PrivateAttr
    _output_dir: Path = PrivateAttr()
    _realesrgan_path: Optional[str] = PrivateAttr(default=None)

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

    def __init__(self, realesrgan_path: Optional[str] = None, **kwargs):
        """
        Initialize the ImageProcessingTool.

        Args:
            realesrgan_path: Path to the Real-ESRGAN executable (if available).
                This is kept for backward compatibility but not used by default.
        """
        super().__init__(**kwargs)
        
        # Set up output directory
        self._output_dir = Path("output/processed_images")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up Real-ESRGAN path if provided
        self._realesrgan_path = realesrgan_path
        
        print("ImageProcessingTool initialized")

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

        try:
            # Check if the file exists
            if not os.path.exists(image_path):
                print(f"Warning: Image file not found at {image_path}")
                # Create a fallback image
                return self._create_fallback_image()
                
            # Copy the file
            shutil.copy2(image_path, temp_path)
            
            # Ensure the file is readable and writable
            os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
            
            return str(temp_path)
        except Exception as e:
            print(f"Error creating temporary copy: {str(e)}")
            # Create a fallback image
            return self._create_fallback_image()

    def _create_fallback_image(self) -> str:
        """
        Create a fallback image if the original image is not found or cannot be read.
        
        Returns:
            Path to the fallback image
        """
        print("Creating fallback image...")
        
        # Create a temporary directory if it doesn't exist
        temp_dir = Path("output/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a fallback image
        fallback_path = temp_dir / "fallback_image.png"
        
        # Create a simple gradient image
        width, height = 1200, 1800  # 4x6 inches at 300 DPI
        image = Image.new("RGB", (width, height), color=(255, 255, 255))
        
        # Add a gradient
        draw = ImageDraw.Draw(image)
        for y in range(height):
            r = int(255 * (1 - y / height))
            g = int(200 * (y / height))
            b = int(255 * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except IOError:
            font = ImageFont.load_default()
            
        draw.text(
            (width // 2, height // 2),
            "Fallback Image\nOriginal not found",
            fill=(255, 255, 255),
            font=font,
            anchor="mm",
            align="center",
        )
        
        # Save the image
        image.save(fallback_path)
        print(f"Fallback image created at {fallback_path}")
        
        return str(fallback_path)

    def upscale_image(self, image_path: str, scale: int = 4) -> Image.Image:
        """
        Upscale an image using either Real-ESRGAN (if available) or Pillow.

        Args:
            image_path: Path to the input image
            scale: Scale factor for upscaling

        Returns:
            Upscaled image as a PIL Image object
        """
        # Create a temporary copy of the image
        temp_path = self._create_temp_copy(image_path)
        
        # Try to use Real-ESRGAN if available
        if self._realesrgan_path and os.path.exists(self._realesrgan_path):
            try:
                print(f"Upscaling image with Real-ESRGAN (scale={scale})...")
                
                # Create output path
                output_dir = Path("output/temp")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"upscaled_{Path(temp_path).name}"
                
                # Run Real-ESRGAN
                cmd = [
                    self._realesrgan_path,
                    "-i", temp_path,
                    "-o", str(output_path),
                    "-s", str(scale),
                    "-n", "realesrgan-x4plus",  # Use the x4plus model
                ]
                
                # Run the command
                subprocess.run(cmd, check=True)
                
                # Load the upscaled image
                if os.path.exists(output_path):
                    return Image.open(output_path)
            except Exception as e:
                print(f"Error using Real-ESRGAN: {str(e)}")
                print("Falling back to Pillow for upscaling...")
        
        # Fallback to Pillow for upscaling
        try:
            # Load the image
            image = Image.open(temp_path)
            
            # Get original dimensions
            width, height = image.size
            
            # Calculate new dimensions
            new_width = width * scale
            new_height = height * scale
            
            # Resize the image using Lanczos resampling (high quality)
            upscaled = image.resize((new_width, new_height), Image.LANCZOS)
            
            # Apply some enhancements to improve quality
            enhancer = ImageEnhance.Sharpness(upscaled)
            upscaled = enhancer.enhance(1.5)  # Increase sharpness
            
            enhancer = ImageEnhance.Contrast(upscaled)
            upscaled = enhancer.enhance(1.2)  # Increase contrast slightly
            
            return upscaled
        except Exception as e:
            print(f"Error upscaling image with Pillow: {str(e)}")
            
            # Create a fallback image
            fallback_path = self._create_fallback_image()
            return Image.open(fallback_path)

    def prepare_print_canvas(
        self, size_name: str, aspect_ratio: str = None
    ) -> Image.Image:
        """
        Create a blank canvas for the specified print size.

        Args:
            size_name: Name of the print size (e.g., "4x6", "5x7", etc.)
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)

        Returns:
            Blank canvas as a PIL Image object
        """
        # Get the appropriate print sizes based on aspect ratio
        print_sizes = self.get_print_sizes_for_aspect_ratio(aspect_ratio)
        
        # Check if the size exists
        if size_name not in print_sizes:
            raise ValueError(f"Invalid print size: {size_name}")
        
        # Get dimensions
        dimensions = print_sizes[size_name]
        width = dimensions["width"]
        height = dimensions["height"]
        
        # Create a blank canvas
        canvas = Image.new("RGB", (width, height), color=(255, 255, 255))
        
        return canvas

    def center_image_on_canvas(
        self, image: Image.Image, canvas: Image.Image, fill_canvas: bool = True
    ) -> Image.Image:
        """
        Center an image on a canvas, either filling the canvas or preserving the aspect ratio.

        Args:
            image: Image to center
            canvas: Canvas to center the image on
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.

        Returns:
            Canvas with the image centered on it
        """
        # Get dimensions
        img_width, img_height = image.size
        canvas_width, canvas_height = canvas.size
        
        # Calculate aspect ratios
        img_aspect = img_width / img_height
        canvas_aspect = canvas_width / canvas_height
        
        # Create a copy of the canvas
        result = canvas.copy()
        
        if fill_canvas:
            # Fill the canvas (may crop the image)
            if img_aspect > canvas_aspect:
                # Image is wider than canvas (crop sides)
                new_width = int(img_height * canvas_aspect)
                left = (img_width - new_width) // 2
                image = image.crop((left, 0, left + new_width, img_height))
            else:
                # Image is taller than canvas (crop top/bottom)
                new_height = int(img_width / canvas_aspect)
                top = (img_height - new_height) // 2
                image = image.crop((0, top, img_width, top + new_height))
            
            # Resize to fit canvas
            image = image.resize((canvas_width, canvas_height), Image.LANCZOS)
            result.paste(image, (0, 0))
        else:
            # Preserve aspect ratio (may add borders)
            if img_aspect > canvas_aspect:
                # Image is wider than canvas (fit to width)
                new_height = int(canvas_width / img_aspect)
                image = image.resize((canvas_width, new_height), Image.LANCZOS)
                top = (canvas_height - new_height) // 2
                result.paste(image, (0, top))
            else:
                # Image is taller than canvas (fit to height)
                new_width = int(canvas_height * img_aspect)
                image = image.resize((new_width, canvas_height), Image.LANCZOS)
                left = (canvas_width - new_width) // 2
                result.paste(image, (left, 0))
        
        return result

    def enhance_image_for_print(self, image: Image.Image, preserve_colors: bool = True) -> Image.Image:
        """
        Enhance an image for print quality.

        Args:
            image: Image to enhance
            preserve_colors: If True, will minimize color adjustments to preserve original colors.
                            If False, will apply standard enhancements for print.

        Returns:
            Enhanced image
        """
        # Apply a slight sharpening filter for better print quality (this doesn't affect colors)
        image = image.filter(ImageFilter.SHARPEN)
        
        if not preserve_colors:
            # Standard print enhancements (more vibrant)
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)  # Increase contrast by 20%
            
            # Enhance color
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.1)  # Increase color saturation by 10%
            
            # Enhance brightness
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.05)  # Increase brightness by 5%
        else:
            # Minimal adjustments to preserve original colors
            # Very slight contrast adjustment for print clarity
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.05)  # Minimal contrast increase (5%)
            
            # No color saturation adjustment to preserve original colors
            
            # No brightness adjustment to preserve original colors
        
        return image

    def prepare_image_for_print(
        self,
        image_path: str,
        size_name: str,
        output_filename: Optional[str] = None,
        fill_canvas: bool = True,
        aspect_ratio: str = None,
        preserve_colors: bool = True,
    ) -> str:
        """
        Prepare an image for print at the specified size.

        Args:
            image_path: Path to the input image
            size_name: Name of the print size (e.g., "4x6", "5x7", etc.)
            output_filename: Optional filename for the output image
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)
            preserve_colors: If True, will minimize color adjustments to preserve original colors.
                            If False, will apply standard enhancements for print.

        Returns:
            Path to the prepared image
        """
        try:
            # Create a temporary copy of the image
            temp_path = self._create_temp_copy(image_path)
            
            # Load the image
            image = Image.open(temp_path)
            
            # Upscale the image if needed
            img_width, img_height = image.size
            
            # Get the appropriate print sizes based on aspect ratio
            print_sizes = self.get_print_sizes_for_aspect_ratio(aspect_ratio)
            
            # Check if the size exists
            if size_name not in print_sizes:
                raise ValueError(f"Invalid print size: {size_name}")
            
            # Get target dimensions
            dimensions = print_sizes[size_name]
            target_width = dimensions["width"]
            target_height = dimensions["height"]
            
            # Determine if upscaling is needed
            if img_width < target_width or img_height < target_height:
                # Calculate scale factor
                width_scale = target_width / img_width
                height_scale = target_height / img_height
                scale = max(width_scale, height_scale)
                
                # Upscale the image
                image = self.upscale_image(temp_path, scale=int(scale))
            
            # Create a canvas for the print size
            canvas = self.prepare_print_canvas(size_name, aspect_ratio)
            
            # Center the image on the canvas
            result = self.center_image_on_canvas(image, canvas, fill_canvas)
            
            # Enhance the image for print
            result = self.enhance_image_for_print(result, preserve_colors)
            
            # Create output filename if not provided
            if not output_filename:
                output_filename = f"print_{size_name}.png"
            
            # Create output path
            output_path = self._output_dir / output_filename
            
            # Save the image
            result.save(output_path, "PNG", dpi=(300, 300))
            
            print(f"✓ Prepared image for print size {size_name}: {output_path}")
            return str(output_path)
        
        except Exception as e:
            print(f"Error preparing image for print: {str(e)}")
            traceback.print_exc()
            raise

    def prepare_all_print_sizes(
        self, image_path: str, fill_canvas: bool = True, aspect_ratio: str = None, preserve_colors: bool = True
    ) -> List[str]:
        """
        Prepare an image for all standard print sizes.

        Args:
            image_path: Path to the input image
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)
            preserve_colors: If True, will minimize color adjustments to preserve original colors.
                            If False, will apply standard enhancements for print.

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
                    preserve_colors=preserve_colors,
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

    def _run(
        self, image_path: str, fill_canvas: bool = True, aspect_ratio: str = None, preserve_colors: bool = True
    ) -> List[str]:
        """
        Process an image for all standard print sizes.

        Args:
            image_path: Path to the input image
            fill_canvas: If True, image will fill the entire canvas (cropping if necessary).
                         If False, image will be centered with white borders.
            aspect_ratio: The aspect ratio to use ('portrait', 'landscape', or None for default)
            preserve_colors: If True, will minimize color adjustments to preserve original colors.
                            If False, will apply standard enhancements for print.

        Returns:
            List of paths to the processed images
        """
        print(f"Processing image with aspect_ratio={aspect_ratio}, fill_canvas={fill_canvas}, preserve_colors={preserve_colors}")
        return self.prepare_all_print_sizes(
            image_path,
            fill_canvas=fill_canvas,
            aspect_ratio=aspect_ratio,
            preserve_colors=preserve_colors,
        )

    def run(self, input_str: str) -> str:
        """
        Run the tool with the provided input.

        Args:
            input_str: Either a direct image path or a JSON string with parameters
                       including 'image_path' and optionally 'aspect_ratio', 'fill_canvas', and 'preserve_colors'

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
                    preserve_colors = input_data.get("preserve_colors", True)  # Default to preserving colors

                    if not image_path:
                        return (
                            "Error: Missing required field 'image_path' in JSON input"
                        )

                    print(
                        f"Processing image with aspect_ratio={aspect_ratio}, fill_canvas={fill_canvas}, preserve_colors={preserve_colors}"
                    )
                    output_paths = self._run(
                        image_path, 
                        fill_canvas=fill_canvas, 
                        aspect_ratio=aspect_ratio,
                        preserve_colors=preserve_colors
                    )
                    return json.dumps(output_paths)
            except json.JSONDecodeError:
                # Not JSON, treat as direct image path
                print("Input is not JSON, treating as direct image path")
                output_paths = self._run(input_str)
                return json.dumps(output_paths)

        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return error_msg 