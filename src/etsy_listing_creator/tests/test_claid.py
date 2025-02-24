import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image
from src.etsy_listing_creator.tools.claid import ClaidImageTool

class TestClaidImageTool(unittest.TestCase):
    def setUp(self):
        # Set up environment variable for testing
        os.environ["CLAID_API_KEY"] = "test_key"
        self.tool = ClaidImageTool()
        
        # Create a test image
        self.test_image_path = Path("test_input.png")
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.test_image_path)
        
    def tearDown(self):
        # Clean up test files and directories
        if self.test_image_path.exists():
            self.test_image_path.unlink()
            
        if Path("output/processed_images").exists():
            for file in Path("output/processed_images").glob("*.jpg"):
                file.unlink()
            Path("output/processed_images").rmdir()
        if Path("output").exists():
            Path("output").rmdir()
        
        # Remove test environment variable safely
        os.environ.pop("CLAID_API_KEY", None)

    def test_initialization(self):
        """Test if the tool initializes correctly with API key"""
        self.assertEqual(self.tool._api_key, "test_key")
        self.assertEqual(self.tool._base_url, "https://api.claid.ai")
        self.assertTrue(Path("output/processed_images").exists())

    def test_initialization_without_api_key(self):
        """Test if tool raises error when API key is missing"""
        if "CLAID_API_KEY" in os.environ:
            del os.environ["CLAID_API_KEY"]
        
        with self.assertRaises(ValueError):
            ClaidImageTool()

    def test_get_headers(self):
        """Test if headers are correctly generated"""
        headers = self.tool._get_headers()
        self.assertEqual(headers["Host"], "api.claid.ai")
        self.assertEqual(headers["Authorization"], "Bearer test_key")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch('requests.post')
    @patch('requests.get')
    def test_run_successful(self, mock_get, mock_post):
        """Test successful image processing workflow"""
        # Mock upload response
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 200
        mock_upload_response.json.return_value = {"url": "https://test.com/uploaded.jpg"}
        
        # Mock process response
        mock_process_response = MagicMock()
        mock_process_response.status_code = 200
        mock_process_response.json.return_value = {"url": "https://test.com/processed.jpg"}
        
        # Mock download response
        mock_download_response = MagicMock()
        mock_download_response.status_code = 200
        mock_download_response.content = b"processed_image_data"
        
        # Set up the mock responses
        mock_post.side_effect = [mock_upload_response, mock_process_response]
        mock_get.return_value = mock_download_response

        # Mock PIL Image.open to return proper size and DPI
        mock_image = MagicMock()
        mock_image.size = (100, 100)  # Set as tuple
        mock_image.info = {"dpi": (300, 300)}
        mock_image.__enter__ = MagicMock(return_value=mock_image)
        mock_image.__exit__ = MagicMock(return_value=None)
        
        with patch('PIL.Image.open', return_value=mock_image):
            result = self.tool._run(str(self.test_image_path))
        
        # Verify the result
        expected_path = str(Path("output/processed_images/processed_test_input.jpg"))
        self.assertEqual(result, expected_path)
        self.assertTrue(Path(result).exists())

        # Verify API calls
        self.assertEqual(mock_post.call_count, 2)  # Upload and process calls
        self.assertEqual(mock_get.call_count, 1)   # Download call

    @patch('requests.post')
    def test_upload_failure(self, mock_post):
        """Test when image upload fails"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Upload failed"
        mock_post.return_value = mock_response

        # Mock PIL Image.open with proper size
        mock_image = MagicMock()
        mock_image.size = (100, 100)  # Set as tuple
        mock_image.__enter__ = MagicMock(return_value=mock_image)
        mock_image.__exit__ = MagicMock(return_value=None)
        
        with patch('PIL.Image.open', return_value=mock_image):
            with self.assertRaises(RuntimeError) as context:
                self.tool._run(str(self.test_image_path))
            
            self.assertIn("Failed to upload image", str(context.exception))

    @patch('requests.post')
    def test_process_failure(self, mock_post):
        """Test when image processing fails"""
        # Mock successful upload
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 200
        mock_upload_response.json.return_value = {"url": "https://test.com/uploaded.jpg"}
        
        # Mock failed processing
        mock_process_response = MagicMock()
        mock_process_response.status_code = 400
        mock_process_response.text = "Processing failed"
        
        mock_post.side_effect = [mock_upload_response, mock_process_response]

        # Mock PIL Image.open with proper size
        mock_image = MagicMock()
        mock_image.size = (100, 100)  # Set as tuple
        mock_image.__enter__ = MagicMock(return_value=mock_image)
        mock_image.__exit__ = MagicMock(return_value=None)
        
        with patch('PIL.Image.open', return_value=mock_image):
            with self.assertRaises(RuntimeError) as context:
                self.tool._run(str(self.test_image_path))
            
            self.assertIn("Failed to process image", str(context.exception))

    @patch('requests.post')
    @patch('requests.get')
    def test_low_dpi_error(self, mock_get, mock_post):
        """Test when processed image has low DPI"""
        # Mock successful upload and process
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 200
        mock_upload_response.json.return_value = {"url": "https://test.com/uploaded.jpg"}
        
        mock_process_response = MagicMock()
        mock_process_response.status_code = 200
        mock_process_response.json.return_value = {"url": "https://test.com/processed.jpg"}
        
        mock_post.side_effect = [mock_upload_response, mock_process_response]

        # Mock successful download
        mock_download_response = MagicMock()
        mock_download_response.status_code = 200
        mock_download_response.content = b"processed_image_data"
        mock_get.return_value = mock_download_response

        # Mock PIL Image.open for initial size check and final DPI check
        mock_image_high = MagicMock()
        mock_image_high.size = (100, 100)  # Set as tuple
        mock_image_high.__enter__ = MagicMock(return_value=mock_image_high)
        mock_image_high.__exit__ = MagicMock(return_value=None)
        
        mock_image_low = MagicMock()
        mock_image_low.info = {"dpi": (72, 72)}
        mock_image_low.__enter__ = MagicMock(return_value=mock_image_low)
        mock_image_low.__exit__ = MagicMock(return_value=None)
        
        with patch('PIL.Image.open', side_effect=[mock_image_high, mock_image_low]):
            with self.assertRaises(ValueError) as context:
                self.tool._run(str(self.test_image_path))
            
            self.assertEqual(str(context.exception), "Failed to achieve required DPI")

if __name__ == '__main__':
    unittest.main() 