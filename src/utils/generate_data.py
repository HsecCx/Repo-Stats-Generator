from dotenv import load_dotenv
import os
from utils.utils import create_set_from_txt
from utils.utils import write_json_to_file
from dotenv import load_dotenv
from models.RepositoryDataFetcher import RepositoryFetcher

load_dotenv()
GIT_API_KEY = os.environ.get("GIT_API_KEY")
HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': f'Bearer {GIT_API_KEY}',
    'X-GitHub-Api-Version': '2022-11-28'
}

def get_git_repo_url(repo_file_path):
    return create_set_from_txt(repo_file_path)

def collect_data(git_urls,repository_fetcher):
    git_repo_data = []
    for git_url in git_urls:
        data = repository_fetcher.get_url_data(git_url)
        git_repo_data.append(data)
    return git_repo_data

def aggregate_repo_data(repo_data_list):
    combined_repo_data = {}

    for repo_data in repo_data_list:
        json_repo_data = repo_data.to_dict()       
        combined_repo_data[repo_data.name] = json_repo_data
    return combined_repo_data


def generate_data():
    git_urls = get_git_repo_url(os.environ.get("GIT_REPOS_LIST_PATH"))
    data_fetcher = RepositoryFetcher(scmType="github", headers=HEADERS)
    
    repo_data = collect_data(git_urls, data_fetcher)
    aggregated_data = aggregate_repo_data(repo_data)
    write_json_to_file(json_obj=aggregated_data, file_path=os.environ.get("DATA_SAVE_PATH"))