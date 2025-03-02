"""
Test script for the PrintPreparationTool.
"""

import os
import shutil
import time
import random
from pathlib import Path
import io

from PIL import Image, ImageDraw, ImageFont

from ..tools.print_prep import PrintPreparationTool


def copy_image_safely(source_path, dest_path, max_retries=3):
    """
    Copy an image file with retry logic to handle locked files.

    Args:
        source_path: Path to the source image
        dest_path: Path to save the copied image
        max_retries: Maximum number of retry attempts

    Returns:
        bool: True if successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            # Try direct file copy first
            shutil.copy2(source_path, dest_path)
            print(f"Successfully copied image on attempt {attempt+1}")
            return True
        except PermissionError as e:
            print(f"Permission error on attempt {attempt+1}: {e}")

            # If direct copy fails, try reading the file into memory and writing it out
            try:
                # Wait a bit before retrying (with increasing delay)
                time.sleep(1 + attempt)

                # Try to open and read the image with PIL
                img = Image.open(source_path)
                img_copy = img.copy()  # Create a copy in memory
                img.close()  # Close the original file

                # Save the in-memory copy to the destination
                img_copy.save(dest_path)
                print(f"Successfully copied image using PIL on attempt {attempt+1}")
                return True
            except Exception as e2:
                print(f"PIL copy failed on attempt {attempt+1}: {e2}")

                if attempt == max_retries - 1:
                    print(f"Failed to copy image after {max_retries} attempts")
                    return False

                # Wait before next attempt
                time.sleep(2 + attempt)

    return False


def test_print_prep():
    """Test the PrintPreparationTool with a sample image."""
    # Create the tool
    tool = PrintPreparationTool()

    # Find a sample image to test with or create one
    output_dir = Path("output/images")
    test_dir = Path("output/test_images")
    test_dir.mkdir(parents=True, exist_ok=True)

    # Look for existing images
    image_path = None
    if output_dir.exists():
        image_files = list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpg"))
        if image_files:
            # Choose a random image to reduce chances of it being locked
            source_image = str(random.choice(image_files))
            print(f"Found existing image: {source_image}")

            # Create a unique filename for the copy to avoid conflicts
            timestamp = int(time.time())
            test_image = test_dir / f"test_copy_{timestamp}_{Path(source_image).name}"

            # Try to copy the image safely
            if copy_image_safely(source_image, test_image):
                print(f"Created copy at: {test_image}")
                image_path = str(test_image)
            else:
                print("Could not copy existing image, will create a new one")
                image_path = None

    # If no image was found or copy failed, create a test image
    if not image_path:
        print("Creating a test image...")
        # Create a test image using PIL
        timestamp = int(time.time())
        test_image = test_dir / f"test_image_{timestamp}.png"
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Draw a blue rectangle
        draw.rectangle([(100, 100), (700, 500)], fill=(0, 0, 255))

        # Add text
        try:
            # Try to use a system font
            font = ImageFont.truetype("arial.ttf", 36)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()

        draw.text(
            (400, 300), "Test Image", fill=(255, 255, 255), font=font, anchor="mm"
        )

        # Save the image
        img.save(test_image)
        print(f"Created test image at: {test_image}")
        image_path = str(test_image)

    print(f"\nTesting with image: {image_path}\n")

    # Test preparing a single print size
    print("Testing single print size preparation...")
    try:
        result = tool.prepare_image_for_print(image_path, "8x10")
        print(f"Successfully prepared image for 8x10: {result}")
        assert os.path.exists(result), "Output file does not exist"
    except Exception as e:
        print(f"Error preparing single print size: {e}")
        raise

    # Test preparing all print sizes
    print("\nTesting all print sizes preparation...")
    try:
        results = tool.prepare_all_print_sizes(image_path)
        print(f"Successfully prepared {len(results)} print sizes")
        for path in results:
            assert os.path.exists(path), f"Output file does not exist: {path}"
            print(f"  - {Path(path).name}")
    except Exception as e:
        print(f"Error preparing all print sizes: {e}")
        raise

    print("\nAll tests passed!")


if __name__ == "__main__":
    test_print_prep()
