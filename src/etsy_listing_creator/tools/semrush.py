import os
from typing import Dict, List

import requests
from pydantic import Field, PrivateAttr

from crewai.tools import BaseTool

class SemrushTool(BaseTool):
    name: str = "Semrush SEO Researcher"
    description: str = """
    Research keywords and SEO data using Semrush API.
    Input should be a base keyword or topic.
    Returns keyword suggestions, search volumes, and competition data.
    """

    # Private attributes using Pydantic's PrivateAttr
    _api_key: str = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_key = os.getenv("SEMRUSH_API_KEY")
        if not self._api_key:
            raise ValueError("SEMRUSH_API_KEY environment variable is required")

    def _run(self, keyword: str) -> Dict[str, List[Dict]]:
        """
        Research keywords using Semrush API.
        
        Args:
            keyword: Base keyword or topic to research
            
        Returns:
            Dictionary containing keyword suggestions and metrics
        """
        # Base URL for Semrush API
        base_url = "https://api.semrush.com"

        # Get keyword suggestions
        keyword_suggestions = self._get_keyword_suggestions(base_url, keyword)

        # Get search volumes
        search_volumes = self._get_search_volumes(base_url, keyword_suggestions)

        # Get competition data
        competition_data = self._get_competition_data(base_url, keyword)

        return {
            "suggestions": keyword_suggestions,
            "volumes": search_volumes,
            "competition": competition_data
        }

    def _get_keyword_suggestions(self, base_url: str, keyword: str) -> List[Dict]:
        """Get keyword suggestions from Semrush."""
        endpoint = f"{base_url}/keywords_suggestions"
        params = {
            "key": self._api_key,
            "type": "phrase_these",
            "phrase": keyword,
            "database": "us"
        }

        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to get keyword suggestions: {response.text}")

        return response.json()

    def _get_search_volumes(self, base_url: str, keywords: List[Dict]) -> List[Dict]:
        """Get search volumes for keywords."""
        endpoint = f"{base_url}/analytics/ta/keyword_volume"
        keyword_list = [k["keyword"] for k in keywords]
        params = {
            "key": self._api_key,
            "keywords": ",".join(keyword_list),
            "database": "us"
        }

        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to get search volumes: {response.text}")

        return response.json()

    def _get_competition_data(self, base_url: str, keyword: str) -> List[Dict]:
        """Get competition data for the keyword."""
        endpoint = f"{base_url}/analytics/ta/keyword_competition"
        params = {
            "key": self._api_key,
            "keyword": keyword,
            "database": "us"
        }

        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            raise RuntimeError(f"Failed to get competition data: {response.text}")

        return response.json() 