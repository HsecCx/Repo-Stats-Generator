import requests
import os
import logging
from dotenv import load_dotenv
from typing import Any, Optional

load_dotenv()

class GithubAPIHandler:
    
    def __init__(self, headers: dict, repo_name: Optional[str] = None, org: Optional[str] = None) -> None:
        self.headers = headers
        self.repo_name = repo_name
        self.org_name = self.set_org_name(org)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        logging.info(f"Making a request to: {url}")
        response = requests.request(method, url, headers=self.headers, **kwargs)
        if response.status_code != 200:
            logging.error(f"Request to {url} failed with status code {response.status_code}: {response.text}")
            response.raise_for_status()
        return response

    def remote_github_repo_exists(self) -> dict:
        self._ensure_req_info()
        url = f"https://api.github.com/repos/{self.org}/{self.repo_name}"
        response = self._request('GET', url)
        exists = response.ok
        return exists

    def get_github_org_repo_list(self) -> list:
        url = f"https://api.github.com/orgs/{self.org}/repos"
        response = self._request('GET', url)
        return [repo['clone_url'] for repo in response.json()]
    
    def get_last_commit_date(self, url: str = None) -> str:
        self._ensure_req_info()
        response = self._request('GET', url)
        last_commit = response.json()[0]['commit']['author']['date']
        return last_commit

    def get_github_repo_languages_stats(self, owner: Optional[str] = None) -> dict:
        self._ensure_req_info()
        owner = owner or self.org
        url = f"https://api.github.com/repos/{owner}/{self.repo_name}/languages"
        response = self._request('GET', url)
        return self.__set_languague_percentages(response.json())
    
    def __set_languague_percentages(self, response_data: dict) -> dict:
        total_lines = sum(response_data.values())
        percentages = {k: round((v / total_lines) * 100, 2) for k, v in response_data.items()}
        return percentages

    def set_repo_name(self, repo_name: Optional[str] = None) -> None:
        if not repo_name:
            raise ValueError("Repository name is required but was not provided.")
        self.repo_name = repo_name
    
    def set_org_name(self, org_name: Optional[str] = None) -> None:
        if org_name == "use_environment":
            self.org = os.getenv("GITHUB_ORG", "default_org_name")
            if not self.org:
                raise ValueError("GITHUB_ORG environment variable is not set")
        elif org_name:
            self.org = org_name
        else:
            raise ValueError("Organization name is required")

    def _ensure_req_info(self) -> None:
        if not self.repo_name:
            self.set_repo_name()
