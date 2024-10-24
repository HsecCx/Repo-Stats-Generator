from view.ui import MainWindow
from PyQt5.QtWidgets import QApplication
from utils.utils import load_json_from_file
import sys,os
from dotenv import load_dotenv
from json import JSONDecodeError

load_dotenv()

def initial_data_load_handler():
    data_file_path = os.environ.get("DATA_SAVE_PATH")

    if not data_file_path:
        raise ValueError("DATA_SAVE_PATH is not set in the environment.")

    # Check if file doesn't exist or is empty
    if not os.path.exists(data_file_path) or os.path.getsize(data_file_path) == 0:
        print(f"File does not exist or is empty. Creating a new file {data_file_path}")
        # Ensure the directory exists
        os.makedirs(os.path.dirname(data_file_path), exist_ok=True)
        
        with open(os.path.abspath(data_file_path), "w") as f:
            f.write("{}") 
    try:
        data = load_json_from_file(data_file_path)
    except JSONDecodeError as e:
        print(e)
        exit()
        
    return data

def run_main_window():
    data = initial_data_load_handler()         

    # Initialize the application
    app = QApplication(sys.argv)
    
    # Create the main window, passing in the data
    main_window = MainWindow(data)
    
    # Show the main window
    main_window.show()
    
    # Execute the application's event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_main_window()
