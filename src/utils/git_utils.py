import requests
import os
import logging
from dotenv import load_dotenv
from typing import Any, Optional
import subprocess
import re

load_dotenv()


logging.basicConfig(level=logging.INFO)


class GitCommands:
    STATUS = "status"
    FULL_PUSH = "full_push"
    CLONE = "clone"


class GithubActionManager:
    
    def _git_command_result_handler(self, command: str, result: subprocess.CompletedProcess) -> Any:
        if command == GitCommands.STATUS:
            return "nothing to commit" not in str(result.stdout)
        if command == GitCommands.FULL_PUSH:
            return result
        return result

    def git_run_commands(self, command: str, working_directory: str, git_url: Optional[str] = None) -> list:
        git_commands = []
        results = []
        
        if command == GitCommands.STATUS:
            git_commands.append(['git', 'status'])
        elif command == GitCommands.FULL_PUSH:
            git_commands.extend([
                ['git', 'add', '--all'],
                ['git', 'commit', '-m', "Updates"],
                ['git', "push", "-u", "origin"]
            ])
        elif command == GitCommands.CLONE and git_url:
            git_commands.append(['git', 'clone', git_url])
        
        for git_command in git_commands:
            try:
                result = subprocess.run(git_command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=working_directory)
                results.append(self._git_command_result_handler(command, result))
            except subprocess.CalledProcessError as e:
                results.append(f"Error running Git command: {e}\nGIT {command} error output:\n{e.stderr}")
        
        return results


class GithubAPIHandler:
    
    def __init__(self, headers: dict, repo_name: Optional[str] = None, org: Optional[str] = None) -> None:
        self.headers = headers
        self.repo_name = repo_name
        self.org_name = self.set_org_name(org)
        self.base_url_endpoint = "https://api.github.com"

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        logging.info(f"Making a request to: {url}")
        response = requests.request(method, url, headers=self.headers, **kwargs)
        if response.status_code != 200:
            logging.error(f"Request to {url} failed with status code {response.status_code}: {response.text}")
            response.raise_for_status()
        return response

    def remote_github_repo_exists(self) -> dict:
        self._ensure_req_info()
        url = f"{self.base_url_endpoint}/repos/{self.org}/{self.repo_name}"
        response = self._request('GET', url)
        exists = response.ok
        return exists

    def get_github_org_repo_list(self) -> list:
        url = f"{self.base_url_endpoint}/orgs/{self.org}/repos"
        response = self._request('GET', url)
        return [repo['clone_url'] for repo in response.json()]
    
    def get_last_commit_date(self, owner: str = None) -> str:
        self._ensure_req_info()
        url = f"{self.base_url_endpoint}/repos/{owner}/{self.repo_name}/commits"
        response = self._request('GET', url)
        last_commit_data = response.json()
        last_commit_date = self.get_latest_non_bot_commit_date(last_commit_data)
        return last_commit_date

    def get_latest_non_bot_commit_date(self,commits):
        non_bot_commit_date = None
        for commit in commits:
            try:
                author_name = commit.get('commit', {}).get('author', '').get('name', '')
                committer_name = commit.get('commit', {}).get('committer', '').get('name', '')
            except Exception as e:
                logging.error(f"Error getting commit data: {e}")
                #print(commit)
            # Exclude commits by bots (login containing 'bot')
            if not re.search(r'\[bot\]', author_name, re.IGNORECASE) and not re.search(r'\[bot\]', committer_name, re.IGNORECASE):
                author_date = commit['commit']['author']['date']
                if not non_bot_commit_date or author_date > non_bot_commit_date:
                    non_bot_commit_date = author_date
            else:
                # print(author_name, committer_name)
                pass
            
        return non_bot_commit_date.split("T")[0]

    
    def get_github_repo_languages_stats(self, owner: Optional[str] = None) -> dict:
        self._ensure_req_info()
        owner = owner or self.org
        url = f"{self.base_url_endpoint}/repos/{owner}/{self.repo_name}/languages"
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

