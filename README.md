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

Create a .env folder in the root with the formatting
```
GIT_API_KEY=<api_key>
DATA_SAVE_PATH=<absolute path where you want to save your data>
GIT_REPOS_LIST_PATH=<absolute path to where your list of repo urls is>
```
Create a txt file with the list of urls you want. Seperate each one with a newline/return.


## License

This project is licensed under the MIT License.