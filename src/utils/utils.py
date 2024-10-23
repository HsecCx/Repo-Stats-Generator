from dotenv import load_dotenv
import shutil, os, stat, re, json, subprocess
from typing import Optional, Any
import logging
from pathlib import Path

load_dotenv()

# Setup logging instead of using print statements
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Regex patterns stored as constants for reusability
GITHUB_REPO_PATTERN = r'/([^/]+)\.git$'
GITHUB_OWNER_PATTERN = r'github\.com\/(.*?)\/'
SCM_PATTERN = r'(\w+)\.\w+($|\/)'

def validate_path(target_path: str) -> tuple[bool, str]:
    """
    Validates a given path by checking if it exists and preventing path traversal.

    :param target_path: The path to validate (can be a file or directory).
    :return: A tuple (bool, message), where the bool indicates if the path is valid, and the message provides an explanation.
    """
    target_path = os.path.abspath(os.path.normpath(target_path))

    if not os.path.exists(target_path):
        return False, f"Error: Path '{target_path}' does not exist."
    
    if not (os.path.isfile(target_path) or os.path.isdir(target_path)):
        return False, f"Error: '{target_path}' is neither a file nor a directory."
    
    return True, "Path is valid."

def extract_from_url(url: str, pattern: str, item_description: str) -> str:
    """
    Extract a part of a URL using a regex pattern.

    :param url: The URL to extract from.
    :param pattern: The regex pattern to use for extraction.
    :param item_description: Description of the item being extracted for logging purposes.
    :return: The extracted item from the URL, or exit if not found.
    """
    match = re.search(pattern, url)
    if match:
        return match.group(1).lower()
    else:
        logging.error(f"{item_description} not found in URL. Make sure the URL is correct: {url}")
        raise ValueError(f"{item_description} extraction failed")

def get_repo_name_from_url(url: str) -> str:
    return extract_from_url(url, GITHUB_REPO_PATTERN, "Repository name")

def get_owner_from_url(url: str, source="github") -> str:
    if source == "github":
        return extract_from_url(url, GITHUB_OWNER_PATTERN, "Owner")

def get_scm_from_url(url: str) -> str:
    return extract_from_url(url, SCM_PATTERN, "SCM")

def copy_folder(src: str, dest: str) -> None:
    """Copies a folder from src to dest."""
    if os.path.exists(src):
        shutil.copytree(src, dest)
        logging.info(f"Copied folder from {src} to {dest}")
    else:
        logging.error(f"Source folder {src} does not exist.")

def move_folder(src: str, dest: str) -> None:
    """Moves a folder from src to dest."""
    if os.path.exists(src):
        shutil.move(src, dest)
        logging.info(f"Moved folder from {src} to {dest}")
    else:
        logging.error(f"Source folder {src} does not exist.")

def create_set_from_txt(file_path: str) -> list:
    """Creates a sorted set of unique entries from a text file."""
    try:
        with open(file_path, "r+", encoding="utf-8") as f:
            text_list = [line.strip() for line in f.readlines()]
        
        if not text_list:
            logging.error("No data found in the file. Ensure the file has data, exists, or the path is correct.")
            raise ValueError("File is empty")
        
        unique_text_list = set(text_list)
        return sorted(unique_text_list, key=get_repo_name_from_url)
    
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        raise

def remove_readonly(func, path, excinfo):
    """Removes read-only restrictions to delete files."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def force_rmtree(path: str) -> None:
    """Forcefully removes a directory and its contents."""
    shutil.rmtree(path, onerror=remove_readonly)

def list_immediate_subdirectories(parent_dir: str) -> list:
    """Returns a list of immediate subdirectories in a given directory."""
    try:
        return [os.path.join(parent_dir, name) for name in os.listdir(parent_dir)
                if os.path.isdir(os.path.join(parent_dir, name))]
    except FileNotFoundError:
        logging.error(f"The directory {parent_dir} does not exist.")
        return []

def load_json_from_file(file_path: str) -> Any:
    """Loads a JSON file."""
    is_valid, message = validate_path(file_path)
    if not is_valid:
        logging.error(message)
        raise FileNotFoundError(message)
    try:
        with open(file_path, 'r', encoding="utf-8") as file:
            return json.load(file)
    except json.decoder.JSONDecodeError:
        logging.error(f"Error decoding JSON from {file_path}")
        raise

def write_json_to_file(file_path: str, json_obj: dict) -> None:
    """Saves a JSON object to a file."""
    try:
        with open(file_path, "w+", encoding="utf-8") as file:
            json.dump(json_obj, file, indent=4)
        logging.info(f"JSON successfully saved to {file_path}")
    except Exception as e:
        logging.error(f"Error saving JSON: {e}")
        raise

def find_keys_in_json(json_obj: dict, target_key: str, path: str = "") -> list:
    """
    Recursively search for all instances of a specific key in a JSON object.
    """
    results = []

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            current_path = f"{path}/{key}" if path else key
            if key == target_key:
                results.append({"search_key": key, "values": value, "key_path": current_path})
            if isinstance(value, (dict, list)):
                results.extend(find_keys_in_json(value, target_key, current_path))

    elif isinstance(json_obj, list):
        for index, item in enumerate(json_obj):
            current_path = f"{path}[{index + 1}]"
            if isinstance(item, (dict, list)):
                results.extend(find_keys_in_json(item, target_key, current_path))

    return results

def __navigate_json_path(json_obj: dict, key_path: str) -> tuple:
    """Navigate through a JSON object based on the given key path."""
    keys = key_path.split("/")
    current_item = json_obj

    for key in keys[:-1]:
        if key.isdigit():
            key = int(key) - 1
        current_item = current_item[key]

    final_key = keys[-1]
    return current_item, final_key

def delete_json_key_at_path(json_obj: dict, key_path: str) -> None:
    """Delete a specific key from a JSON object based on the key path."""
    current_item, final_key = __navigate_json_path(json_obj, key_path)
    
    if final_key.isdigit():
        del current_item[int(final_key) - 1]
    else:
        del current_item[final_key]
    logging.info(f"Deleted key at path: {key_path}")

def update_json_key_at_path(json_obj: dict, key_path: str, update_value: Any) -> None:
    """Update a specific key in a JSON object based on the key path."""
    current_item, final_key = __navigate_json_path(json_obj, key_path)
    
    if final_key.isdigit():
        current_item[int(final_key) - 1] = update_value
    else:
        current_item[final_key] = update_value
    logging.info(f"Updated key at path: {key_path} with value: {update_value}")

def modify_json_key(json_obj: dict, json_key: str, json_parents_path: Optional[str], action: str, update_value: Any = None) -> dict:
    """Process a JSON key by either deleting or updating it based on the action specified."""
    find_key_results = find_keys_in_json(json_obj, json_key)
    
    if not find_key_results:
        logging.warning(f"Key '{json_key}' not found.")
        return json_obj

    processed_any = False
    for result in find_key_results:
        if not json_parents_path or (json_parents_path and json_parents_path in result["key_path"]):
            if action == "delete":
                delete_json_key_at_path(json_obj, result["key_path"])
            elif action == "update":
                update_json_key_at_path(json_obj, result["key_path"], update_value)
            processed_any = True

    if not processed_any:
        logging.warning(f"No matching key found for '{json_key}' with the parent path '{json_parents_path}'.")
    
    return json_obj

def parse_scc_output(output: str) -> dict:
    """Parses the output from scc.exe into a dictionary."""
    language_label = "Language"
    files_label = "Files"
    lines_label = "Lines"
    blanks_label = "Blanks"
    comments_label = "Comments"
    code_label = "Code"
    complexity_label = "Complexity"
    data_processed_label = "Size Processed"

    lines = output.split('\n')
    data = {}
    data_processed = None

    regex = re.compile(r'\s{2,}')
    start_collecting = False

    for line in lines:
        if 'Language' in line:
            start_collecting = True
            continue

        if start_collecting:
            if '────────────────' in line or not line.strip():
                continue

            if 'Estimated' in line:
                break

            if 'Processed' in line:
                parts = line.split()
                data_processed = float(parts[4])
                continue

            columns = regex.split(line.strip())
            if len(columns) >= 6:
                language = columns[0]
                files = int(columns[1])
                lines = int(columns[2])
                blanks = int(columns[3])
                comments = int(columns[4])
                code = int(columns[5])
                complexity = int(columns[6]) if len(columns) == 7 else 0

                entry_language_label = "Totals" if language == "Total" else language
                data[entry_language_label] = {
                    files_label: files,
                    lines_label: lines,
                    blanks_label: blanks,
                    comments_label: comments,
                    code_label: code,
                    complexity_label: complexity
                }

    if data_processed is not None:
        data.update({data_processed_label: data_processed})

    return data

def run_scc_on_directory(target_directory: str) -> dict:
    """Runs scc.exe on the specified directory or file using secure path validation."""
    scc_path = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'scc.exe')))

    is_valid, validation_message = validate_path(target_directory)
    if not is_valid:
        logging.error(validation_message)
        raise FileNotFoundError(validation_message)

    try:
        result = subprocess.run([scc_path, os.path.abspath(os.path.normpath(target_directory))],
                                capture_output=True, text=True, encoding='utf-8')

        if result.returncode == 0:
            return parse_scc_output(result.stdout)
        else:
            logging.error(f"Error running scc.exe: {result.stderr}")
            raise RuntimeError(result.stderr)

    except FileNotFoundError:
        logging.error(f"scc.exe not found at {scc_path}")
        raise
