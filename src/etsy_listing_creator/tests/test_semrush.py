import os
import unittest
from unittest.mock import patch, MagicMock

from src.etsy_listing_creator.tools.semrush import SemrushTool

class TestSemrushTool(unittest.TestCase):
    def setUp(self):
        # Set up environment variable for testing
        os.environ["SEMRUSH_API_KEY"] = "test_key"
        self.tool = SemrushTool()
        
    def tearDown(self):
        # Remove test environment variable safely
        os.environ.pop("SEMRUSH_API_KEY", None)

    def test_initialization(self):
        """Test if the tool initializes correctly with API key"""
        self.assertEqual(self.tool._api_key, "test_key")

    def test_initialization_without_api_key(self):
        """Test if tool raises error when API key is missing"""
        if "SEMRUSH_API_KEY" in os.environ:
            del os.environ["SEMRUSH_API_KEY"]
        
        with self.assertRaises(ValueError):
            SemrushTool()

    @patch('requests.get')
    def test_get_keyword_suggestions_successful(self, mock_get):
        """Test successful keyword suggestions retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"keyword": "test keyword 1", "volume": 1000},
            {"keyword": "test keyword 2", "volume": 500}
        ]
        mock_get.return_value = mock_response

        result = self.tool._get_keyword_suggestions("https://api.semrush.com", "test")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["keyword"], "test keyword 1")

    @patch('requests.get')
    def test_get_keyword_suggestions_error(self, mock_get):
        """Test error handling in keyword suggestions"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "API Error"
        mock_get.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.tool._get_keyword_suggestions("https://api.semrush.com", "test")
        self.assertIn("Failed to get keyword suggestions", str(context.exception))

    @patch('requests.get')
    def test_get_search_volumes_successful(self, mock_get):
        """Test successful search volumes retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"keyword": "test keyword 1", "volume": 1000},
            {"keyword": "test keyword 2", "volume": 500}
        ]
        mock_get.return_value = mock_response

        keywords = [{"keyword": "test keyword 1"}, {"keyword": "test keyword 2"}]
        result = self.tool._get_search_volumes("https://api.semrush.com", keywords)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["volume"], 1000)

    @patch('requests.get')
    def test_get_search_volumes_error(self, mock_get):
        """Test error handling in search volumes retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "API Error"
        mock_get.return_value = mock_response

        keywords = [{"keyword": "test keyword"}]
        with self.assertRaises(RuntimeError) as context:
            self.tool._get_search_volumes("https://api.semrush.com", keywords)
        self.assertIn("Failed to get search volumes", str(context.exception))

    @patch('requests.get')
    def test_get_competition_data_successful(self, mock_get):
        """Test successful competition data retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"keyword": "test", "competition": 0.75}
        ]
        mock_get.return_value = mock_response

        result = self.tool._get_competition_data("https://api.semrush.com", "test")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["competition"], 0.75)

    @patch('requests.get')
    def test_get_competition_data_error(self, mock_get):
        """Test error handling in competition data retrieval"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "API Error"
        mock_get.return_value = mock_response

        with self.assertRaises(RuntimeError) as context:
            self.tool._get_competition_data("https://api.semrush.com", "test")
        self.assertIn("Failed to get competition data", str(context.exception))

    @patch.object(SemrushTool, '_get_keyword_suggestions')
    @patch.object(SemrushTool, '_get_search_volumes')
    @patch.object(SemrushTool, '_get_competition_data')
    def test_run_successful(self, mock_competition, mock_volumes, mock_suggestions):
        """Test successful complete workflow"""
        # Mock the responses from each method
        mock_suggestions.return_value = [{"keyword": "test keyword"}]
        mock_volumes.return_value = [{"keyword": "test keyword", "volume": 1000}]
        mock_competition.return_value = [{"keyword": "test keyword", "competition": 0.75}]

        result = self.tool._run("test keyword")
        
        # Verify the structure and content of the result
        self.assertIn("suggestions", result)
        self.assertIn("volumes", result)
        self.assertIn("competition", result)
        self.assertEqual(len(result["suggestions"]), 1)
        self.assertEqual(result["volumes"][0]["volume"], 1000)
        self.assertEqual(result["competition"][0]["competition"], 0.75)

if __name__ == '__main__':
    unittest.main() 