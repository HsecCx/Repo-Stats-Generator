import logging
from typing import Optional
from utils.utils import *
from utils.git_utils import *
from models.Repo import Repo

SUPPORTED_SCM_TYPES = ["github", "bitbucket", "gitlab"]

class RepositoryFetcher:

    def __init__(self, scmType: str, headers: Optional[dict] = None) -> None:
        if scmType not in SUPPORTED_SCM_TYPES:
            raise ValueError(f"Unsupported SCM type: {scmType}. Supported types: {SUPPORTED_SCM_TYPES}")
        
        self.headers = headers
        self.scmType = scmType

    def update_url_data(self, url_json_data: dict, target_url: str, update_value: str, key_to_update: Optional[str] = None) -> dict:
        """
        Updates the URL data for a given target URL.

        :param url_json_data: The existing JSON object to modify.
        :param target_url: The URL of the repository.
        :param update_value: The value to update in the JSON.
        :param key_to_update: The key in the JSON to update.
        :return: Updated JSON object.
        """
        repo_name = get_repo_name_from_url(target_url)
        updated_json_information = modify_json_key(
            json_obj=url_json_data, 
            json_key=key_to_update, 
            json_parents_path=repo_name, 
            update_value=update_value, 
            action="update"
        )
        logging.info(f"Updated URL data for {repo_name}")
        return updated_json_information

    def get_url_data(self, url: str) -> dict:
        """
        Fetches repository data for a given URL.

        :param url: The repository URL.
        :return: A dictionary containing repository details.
        """
        try:
            owner = get_owner_from_url(url)
            repo_name = get_repo_name_from_url(url)
            git_api_handler = GithubAPIHandler(repo_name=repo_name, headers=self.headers, org="use_environment")

            langs = git_api_handler.get_github_repo_languages_stats(owner=owner)
            public_url = url
            last_commit = git_api_handler.get_last_commit_date(owner=owner)
            repo_holder = Repo(
                public_git_url=url,
                name=repo_name,
                languages=langs,
                public_scm=get_scm_from_url(url),
                public_url=public_url.replace(".git", "")
            )
            repo_holder.last_commit_date = last_commit or None
            
            logging.info(f"Successfully fetched URL data for {repo_name}")
        except Exception as e:
            if "429" in str(e.args[0]).lower() and ("rate limit" or "too many requests") in str(e.args[0]).lower():
                exit("Rate limit exceeded. Exiting...")
            logging.error(f"Error fetching data for {url}: {e}")

        return repo_holder
