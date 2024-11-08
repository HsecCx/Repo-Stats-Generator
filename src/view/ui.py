import os
from dotenv import load_dotenv
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QPushButton, QProgressBar, QAbstractItemView
)
from PyQt5.QtCore import Qt, QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from utils.git_utils import GithubActionManager, GitCommands
from view.styles.style import language_colors, qwidget_styling
from utils.utils import create_set_from_txt, write_json_to_file
from models.RepositoryDataFetcher import RepositoryFetcher
from time import sleep

load_dotenv()
GIT_API_KEY = os.environ.get("GIT_API_KEY")
HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'Authorization': f'Bearer {GIT_API_KEY}',
    'X-GitHub-Api-Version': '2022-11-28'
}

def get_git_repo_url(repo_file_path):
    return create_set_from_txt(repo_file_path)

def collect_data(git_urls, repository_fetcher):
    total_items = len(git_urls)
    for i, git_url in enumerate(git_urls, 1):
        data = repository_fetcher.get_url_data(git_url)
        yield data, i, total_items

class DataGenerationSignals(QObject):
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    data_ready = pyqtSignal(dict)
    finished = pyqtSignal()

class DataGenerationTask(QRunnable):
    def __init__(self, git_urls, headers):
        super().__init__()
        self.git_urls = git_urls
        self.headers = headers
        self.signals = DataGenerationSignals()

    def run(self):
        data_fetcher = RepositoryFetcher(scmType="github", headers=self.headers)
        combined_repo_data = {}

        for data, i, total_items in collect_data(self.git_urls, data_fetcher):
            json_repo_data = data.to_dict()
            combined_repo_data[data.name] = json_repo_data

            progress_percent = int(i / total_items * 100)
            self.signals.progress.emit(progress_percent)
            self.signals.status_update.emit(f"Processed {i}/{total_items} repositories.")

        write_json_to_file(json_obj=combined_repo_data, file_path=os.environ.get("DATA_SAVE_PATH"))
        self.signals.data_ready.emit(combined_repo_data)
        self.signals.finished.emit()

class RepoDownloadSignals(QObject):
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal()

class RepoDownloadTask(QRunnable):
    def __init__(self, repo_urls):
        super().__init__()
        self.repo_urls = repo_urls
        self.signals = RepoDownloadSignals()

    def run(self):
        total_repos = len(self.repo_urls)
        git_actions = GithubActionManager()

        for i, repo_url in enumerate(self.repo_urls, 1):
            git_actions.git_run_commands(
                GitCommands.CLONE,
                working_directory=os.environ.get("GIT_CLONE_FOLDER_PATH"),
                git_url=repo_url
            )
            progress_percent = int(i / total_repos * 100)
            self.signals.progress.emit(progress_percent)
            self.signals.status_update.emit(f"Downloaded {i}/{total_repos} repositories: {self.repo_urls}")

        self.signals.finished.emit()

class MainWindow(QWidget):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.threadpool = QThreadPool()
        self.language_colors = language_colors
        self.selected_repo_urls = []
        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle('Repository Language Breakdown')
        self.setGeometry(100, 100, 1000, 700)
        self.setWindowIcon(QIcon('app_icon.png'))  # Ensure 'app_icon.png' exists
        self.apply_stylesheet()

        main_layout = QVBoxLayout()
        main_layout.addLayout(self.create_controls_layout())
        main_layout.addLayout(self.create_content_layout())
        main_layout.addWidget(self.create_status_bar())
        main_layout.addWidget(self.create_progress_bar())

        self.setLayout(main_layout)
        self.populate_table()

    def apply_stylesheet(self) -> None:
        self.setStyleSheet(qwidget_styling)

    def create_controls_layout(self) -> QHBoxLayout:
        controls_layout = QHBoxLayout()

        # Language filter combo box
        self.language_filter_combo = QComboBox()
        self.language_filter_combo.addItem('Filter by Language')
        self.language_filter_combo.addItems(self.get_sorted_languages())
        self.language_filter_combo.currentIndexChanged.connect(self.populate_table)

        controls_layout.addWidget(QLabel('Filter by Language:'))
        controls_layout.addWidget(self.language_filter_combo)

        # Language sort combo box
        self.language_combo = QComboBox()
        self.language_combo.addItem('Select Language to Sort By')
        self.language_combo.addItems(self.get_sorted_languages())
        self.language_combo.currentIndexChanged.connect(self.sort_table)

        controls_layout.addWidget(QLabel('Sort by Language:'))
        controls_layout.addWidget(self.language_combo)

        # Run and Download buttons
        self.run_button = QPushButton('Run Data Generation')
        self.run_button.clicked.connect(self.run_generate_data)
        controls_layout.addWidget(self.run_button)

        self.download_button = QPushButton('Download Selected Repos and count LOC')
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download_selected_repos)
        controls_layout.addWidget(self.download_button)

        return controls_layout

    def create_content_layout(self) -> QHBoxLayout:
        content_layout = QHBoxLayout()

        # Left: Table with repositories
        self.table = self.create_repo_table()
        content_layout.addWidget(self.table)

        # Right: Repository details and matplotlib plot
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.create_details_group())
        right_layout.addWidget(self.create_matplotlib_canvas())
        content_layout.addLayout(right_layout)

        return content_layout

    def create_repo_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Repository', 'Languages', 'Total Languages'])
        table.setSelectionMode(QAbstractItemView.MultiSelection)

        table.itemSelectionChanged.connect(self.handle_repo_selection)

        table.cellClicked.connect(self.display_language_breakdown)
        table.setAlternatingRowColors(True)
        return table

    def create_details_group(self) -> QGroupBox:
        self.details_group = QGroupBox('Repository Details')
        details_layout = QVBoxLayout()

        self.repo_icon_label = QLabel()
        self.repo_details_label = QLabel("Select a repository to see details.")
        self.repo_details_label.setWordWrap(True)
        self.repo_details_label.setOpenExternalLinks(True)

        details_layout.addWidget(self.repo_icon_label)
        details_layout.addWidget(self.repo_details_label)
        self.details_group.setLayout(details_layout)

        return self.details_group

    def create_matplotlib_canvas(self) -> FigureCanvas:
        self.figure = plt.figure(figsize=(5, 4))
        self.canvas = FigureCanvas(self.figure)
        return self.canvas

    def create_status_bar(self) -> QLabel:
        self.status_label = QLabel('')
        return self.status_label

    def create_progress_bar(self) -> QProgressBar:
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setValue(0)
        return self.progress_bar

    def get_sorted_languages(self) -> list:
        languages = {lang for repo_data in self.data.values() for lang in repo_data['languages']}
        return sorted(languages)

    def populate_table(self) -> None:
        self.table.setRowCount(0)
        filter_language = self.language_filter_combo.currentText()
        filter_language = None if filter_language == 'Filter by Language' else filter_language

        for repo_name, repo_data in self.data.items():
            if filter_language and filter_language not in repo_data['languages']:
                continue

            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(repo_name))
            self.table.setItem(row_position, 1, QTableWidgetItem(', '.join(repo_data['languages'].keys())))
            self.table.setItem(row_position, 2, QTableWidgetItem(str(len(repo_data['languages']))))

        self.table.resizeColumnsToContents()
        self.status_label.setText(f'Repositories filtered by {filter_language}' if filter_language else 'All repositories displayed')

    def sort_table(self) -> None:
        selected_language = self.language_combo.currentText()
        selected_language = None if selected_language == 'Select Language to Sort By' else selected_language
        filter_language = self.language_filter_combo.currentText()
        filter_language = None if filter_language == 'Filter by Language' else filter_language

        repo_list = [
            (repo_name, repo_data, repo_data['languages'].get(selected_language, 0))
            for repo_name, repo_data in self.data.items()
            if not filter_language or filter_language in repo_data['languages']
        ]

        sorted_repos = sorted(repo_list, key=lambda x: x[2], reverse=True) if selected_language else repo_list

        self.table.setRowCount(0)
        for repo_name, repo_data, _ in sorted_repos:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(repo_name))
            self.table.setItem(row_position, 1, QTableWidgetItem(', '.join(repo_data['languages'].keys())))
            self.table.setItem(row_position, 2, QTableWidgetItem(str(len(repo_data['languages']))))

        self.table.resizeColumnsToContents()
        self.status_label.setText(f'Repositories sorted by {selected_language}' if selected_language else 'Repositories displayed without sorting')

    def display_language_breakdown(self, row: int, column: int) -> None:
        repo_name_item = self.table.item(row, 0)
        if repo_name_item:
            repo_name = repo_name_item.text()
            repo_data = self.data.get(repo_name)
            if repo_data:
                self.update_repository_details(repo_name, repo_data)
                self.plot_language_breakdown(repo_name, repo_data['languages'])

    def update_repository_details(self, repo_name: str, repo_data: dict) -> None:
        details_html = f"""
        <h3>{repo_name}</h3>
        <p><b>Public SCM:</b> {repo_data['public_scm']}</p>
        <p><b>Public URL:</b> <a href="{repo_data['public_url']}">{repo_data['public_url']}</a></p>
        """
        self.repo_details_label.setText(details_html)
        icon_path = f'icons/{repo_name}.png'
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.repo_icon_label.setPixmap(pixmap)
        else:
            self.repo_icon_label.clear()

    def plot_language_breakdown(self, repo_name: str, languages: dict) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        labels, sizes = zip(*sorted(languages.items(), key=lambda x: x[1], reverse=True))
        colors = [self.language_colors.get(lang, 'grey') for lang in labels]
        ax.barh(labels, sizes, color=colors)
        ax.set_xlabel('Percentage')
        ax.set_title(f'Language Breakdown for {repo_name}')
        ax.invert_yaxis()
        self.figure.tight_layout()
        self.canvas.draw()

    def handle_repo_selection(self) -> None:
        """Handle multi-selection of repositories."""
        selected_items = self.table.selectedItems()
        selected_repo_urls = set()

        for item in selected_items:
            if item.column() == 0:  # Check if the item is in the 'Repository' column
                repo_name = item.text()
                repo_data = self.data.get(repo_name)
                if repo_data and 'public_git_url' in repo_data:
                    selected_repo_urls.add(repo_data['public_git_url'])

        # Update the selected repo URLs and button state
        self.selected_repo_urls = list(selected_repo_urls)
        if self.selected_repo_urls:
            self.download_button.setEnabled(True)
            self.status_label.setText(f"{len(self.selected_repo_urls)} repositories selected.")
        else:
            self.download_button.setEnabled(False)
            self.status_label.setText("No repositories selected.")

    def run_generate_data(self) -> None:
        """Start the data generation using QThreadPool."""
        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting data generation...")

        git_urls = get_git_repo_url(os.environ.get("GIT_REPOS_LIST_PATH"))

        task = DataGenerationTask(git_urls, HEADERS)
        task.signals.progress.connect(self.update_progress_bar)
        task.signals.status_update.connect(self.status_label.setText)
        task.signals.data_ready.connect(self.update_data)
        task.signals.finished.connect(self.on_data_generation_finished)

        self.threadpool.start(task)

    def update_data(self, new_data):
        """Update the data and refresh the table."""
        self.data = new_data
        self.populate_table()

    def on_data_generation_finished(self):
        """Handle actions after data generation is complete."""
        self.run_button.setEnabled(True)
        self.status_label.setText("Data generation completed.")
        self.progress_bar.setValue(100)
        sleep(1)
        self.progress_bar.hide()
        

    def update_progress_bar(self, value: int):
        """Update the progress bar value."""
        self.progress_bar.setValue(value)

    def download_selected_repos(self) -> None:
        """Start the repo download using QThreadPool."""
        if not self.selected_repo_urls:
            self.status_label.setText("No repositories selected for download.")
            return

        self.download_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting repository download...")

        task = RepoDownloadTask(self.selected_repo_urls)
        task.signals.progress.connect(self.update_progress_bar)
        task.signals.status_update.connect(self.status_label.setText)
        task.signals.finished.connect(self.on_repo_download_finished)

        self.threadpool.start(task)

    def on_repo_download_finished(self):
        """Handle actions after repository download is complete."""
        self.download_button.setEnabled(True)
        self.status_label.setText("Repository download completed.")
        self.progress_bar.setValue(100)
