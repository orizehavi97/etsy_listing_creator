import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image
from src.etsy_listing_creator.tools.dynamic_mockup import DynamicMockupTool

class TestDynamicMockupTool(unittest.TestCase):
    def setUp(self):
        # Set up environment variable for testing
        os.environ["DYNAMIC_MOCKUPS_API_KEY"] = "test_key"
        self.tool = DynamicMockupTool()
        
        # Create a test image
        self.test_image_path = Path("test_input.png")
        img = Image.new('RGB', (100, 100), color='red')
        img.save(self.test_image_path)
        
    def tearDown(self):
        # Clean up test files and directories
        if self.test_image_path.exists():
            self.test_image_path.unlink()
            
        if Path("output/mockups").exists():
            for file in Path("output/mockups").glob("*.png"):
                file.unlink()
            Path("output/mockups").rmdir()
        if Path("output").exists():
            Path("output").rmdir()
        
        # Remove test environment variable safely
        os.environ.pop("DYNAMIC_MOCKUPS_API_KEY", None)

    def test_initialization(self):
        """Test if the tool initializes correctly with API key"""
        self.assertEqual(self.tool._api_key, "test_key")
        self.assertEqual(self.tool._base_url, "https://app.dynamicmockups.com/api/v1")
        self.assertTrue(Path("output/mockups").exists())
        self.assertEqual(len(self.tool._templates), 4)

    def test_initialization_without_api_key(self):
        """Test if tool raises error when API key is missing"""
        if "DYNAMIC_MOCKUPS_API_KEY" in os.environ:
            del os.environ["DYNAMIC_MOCKUPS_API_KEY"]
        
        with self.assertRaises(ValueError):
            DynamicMockupTool()

    def test_get_headers(self):
        """Test if headers are correctly generated"""
        headers = self.tool._get_headers()
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(headers["x-api-key"], "test_key")

    @patch('requests.post')
    @patch('requests.get')
    def test_run_successful(self, mock_get, mock_post):
        """Test successful mockup generation"""
        # Mock successful render response
        mock_render_response = MagicMock()
        mock_render_response.status_code = 200
        mock_render_response.json.return_value = {"url": "https://test.com/mockup.png"}
        mock_post.return_value = mock_render_response

        # Mock successful download response
        mock_download_response = MagicMock()
        mock_download_response.status_code = 200
        mock_download_response.content = b"mockup_image_data"
        mock_get.return_value = mock_download_response

        # Run the tool
        result = self.tool._run(str(self.test_image_path))
        
        # Verify the results
        self.assertEqual(len(result), 4)  # One for each template
        for path in result:
            self.assertTrue(Path(path).exists())
            self.assertTrue(path.startswith(str(Path("output/mockups/mockup_"))))

        # Verify API calls
        self.assertEqual(mock_post.call_count, 4)  # One call per template
        self.assertEqual(mock_get.call_count, 4)   # One download per template

    @patch('requests.post')
    def test_run_unauthorized(self, mock_post):
        """Test unauthorized API access"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            self.tool._run(str(self.test_image_path))
        
        self.assertIn("Invalid API key or unauthorized access", str(context.exception))

    @patch('requests.post')
    def test_run_invalid_uuid(self, mock_post):
        """Test invalid mockup UUID"""
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "message": "The selected mockup uuid is invalid.",
            "errors": {
                "mockup_uuid": [
                    "The selected mockup uuid is invalid."
                ]
            }
        }
        mock_post.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            self.tool._run(str(self.test_image_path))
        
        self.assertEqual(str(context.exception), "Invalid mockup UUID provided")

    @patch('requests.post')
    def test_run_rate_limit(self, mock_post):
        """Test rate limit exceeded"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.tool._run(str(self.test_image_path))
        
        self.assertIn("Rate limit exceeded", str(context.exception))

    @patch('requests.post')
    @patch('requests.get')
    def test_run_partial_failure(self, mock_get, mock_post):
        """Test when some mockups fail to generate"""
        # Mock responses for each template
        def mock_render_response(*args, **kwargs):
            data = kwargs.get('json', {})
            template_uuid = data.get('mockup_uuid', '')
            mock = MagicMock()
            
            # Succeed for two templates, fail for two
            if template_uuid in [self.tool._templates["frame-on-wall"], 
                               self.tool._templates["frame-on-desk"]]:
                mock.status_code = 200
                mock.json.return_value = {"url": "https://test.com/mockup.png"}
            else:
                mock.status_code = 400
                mock.text = "API Error"
            return mock

        mock_post.side_effect = mock_render_response

        # Mock successful download response
        mock_download_response = MagicMock()
        mock_download_response.status_code = 200
        mock_download_response.content = b"mockup_image_data"
        mock_get.return_value = mock_download_response

        # Run the tool
        result = self.tool._run(str(self.test_image_path))
        
        # Verify that we got results for successful templates only
        self.assertEqual(len(result), 2)  # Should get 2 successful mockups
        for path in result:
            self.assertTrue(Path(path).exists())
            self.assertTrue("frame-on-wall" in path or "frame-on-desk" in path)

    @patch('requests.post')
    def test_run_complete_failure(self, mock_post):
        """Test when all mockups fail to generate"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Invalid request",
            "errors": {
                "request": ["Invalid request parameters"]
            }
        }
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.tool._run(str(self.test_image_path))
        
        self.assertEqual(str(context.exception), "API request failed: Invalid request")

    @patch('requests.post')
    def test_run_server_error(self, mock_post):
        """Test when server returns 500 error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.tool._run(str(self.test_image_path))
        
        self.assertEqual(str(context.exception), "Server error occurred. Please try again later.")

    @patch('requests.post')
    def test_run_invalid_smart_object(self, mock_post):
        """Test when smart object UUID is invalid"""
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "message": "The selected smart_objects.0.uuid is invalid.",
            "errors": {
                "smart_objects.0.uuid": [
                    "The selected smart_objects.0.uuid is invalid."
                ]
            }
        }
        mock_post.return_value = mock_response

        with self.assertRaises(ValueError) as context:
            self.tool._run(str(self.test_image_path))
        
        self.assertEqual(str(context.exception), "Invalid smart object UUID provided")

if __name__ == '__main__':
    unittest.main() 