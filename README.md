# Repo-Stats-Generator

A repo designed to generate stats and information about repositories

## Features
This script will generate output for the repos in the following json format.  There is also a UI that will show the details of each repo based upon this generated data
```"
"<name>": {
	"public_git_url": "<url>.git",
	"repo name": "<name>",
	"languages": {
		"Python": 86.63,
		"HTML": 7.47,
		"Dockerfile": 5.89
	},
	"public_scm": "github",
	"public_url": "<public_url>"
}
```
## Prerequisites

Installing the requirements.txt file for your environment
`pip install -r /path/to/requirements.txt`

Having git installed.

Create a .env file in the root with the variables:
```
GIT_API_KEY=<api_key>
DATA_SAVE_PATH=<absolute path where you want to save your collected repo data. MUST BE JSON>
GIT_REPOS_LIST_PATH=<absolute path to where your list of repo urls is. MUST BE .TXT>
GIT_CLONE_FOLDER_PATH=<aboslute path of where to clone the git repos to. MUST BE A DIR>
```

Create a txt file with the list of urls you want (GIT_REPOS_LIST_PATH). Seperate each one with a newline/return.

You do not need to create the file that holds the data, but DATA_SAVE_PATH must point to a valid file path (directories will be created if need be by the script though) and it must be a json file. 

GIT_CLONE_FOLDER_PATH is where you can download cloned repos to via the UI. 

## License

This project is licensed under the MIT License.