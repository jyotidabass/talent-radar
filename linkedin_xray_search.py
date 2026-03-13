from typing import List, Dict, Optional
import os
import json
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
import time
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LinkedInProfile:
    url: str
    name: str
    title: str
    company: str
    location: str
    summary: str
    experience: List[Dict]
    education: List[Dict]
    skills: List[str]
    last_updated: datetime

class LinkedInXRaySearch:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    def search(self, query: str, num_results: int = 10) -> List[LinkedInProfile]:
        """Execute X-Ray search and return LinkedIn profiles"""
        profiles = []
        
        # Execute search
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": min(num_results, 10)  # Google CSE limits to 10 per request
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            results = response.json()
            
            # Process each result
            for item in results.get("items", []):
                if "linkedin.com/in/" in item.get("link", ""):
                    profile = self._extract_profile_info(item)
                    if profile:
                        profiles.append(profile)
                        
            # If we need more results, make additional requests
            if num_results > 10:
                start_index = 11
                while len(profiles) < num_results and start_index <= 100:  # Google CSE limits to 100 results
                    params["start"] = start_index
                    response = requests.get(self.base_url, params=params)
                    response.raise_for_status()
                    results = response.json()
                    
                    for item in results.get("items", []):
                        if "linkedin.com/in/" in item.get("link", ""):
                            profile = self._extract_profile_info(item)
                            if profile:
                                profiles.append(profile)
                                
                    start_index += 10
                    time.sleep(1)  # Respect rate limits
                    
        except Exception as e:
            print(f"Error during search: {e}")
            
        return profiles[:num_results]
    
    def _extract_profile_info(self, search_result: Dict) -> Optional[LinkedInProfile]:
        """Extract profile information from search result"""
        try:
            # Extract basic info from search result
            url = search_result.get("link", "")
            title = search_result.get("title", "")
            snippet = search_result.get("snippet", "")
            
            # Parse the title to get name and current role
            name = title.split("|")[0].strip() if "|" in title else title.split("-")[0].strip()
            current_role = title.split("|")[1].strip() if "|" in title else ""
            
            # Extract company from current role
            company = ""
            if " at " in current_role:
                company = current_role.split(" at ")[1].strip()
            
            # Extract location from snippet
            location = ""
            if " · " in snippet:
                location = snippet.split(" · ")[0].strip()
            
            # Create profile object
            profile = LinkedInProfile(
                url=url,
                name=name,
                title=current_role,
                company=company,
                location=location,
                summary=snippet,
                experience=[],  # Would need additional scraping to get these
                education=[],   # Would need additional scraping to get these
                skills=[],      # Would need additional scraping to get these
                last_updated=datetime.now()
            )
            
            return profile
            
        except Exception as e:
            print(f"Error extracting profile info: {e}")
            return None

# Example usage
if __name__ == "__main__":
    searcher = LinkedInXRaySearch()
    
    # Example search query
    query = 'site:linkedin.com/in ("Senior Frontend Engineer" OR "Frontend Developer") ("React" OR "TypeScript") ("San Francisco" OR "Remote") -intitle:"profiles" -inurl:"dir"'
    
    # Execute search
    profiles = searcher.search(query, num_results=5)
    
    # Print results
    for profile in profiles:
        print(f"\nName: {profile.name}")
        print(f"Title: {profile.title}")
        print(f"Company: {profile.company}")
        print(f"Location: {profile.location}")
        print(f"URL: {profile.url}")
        print("---") 