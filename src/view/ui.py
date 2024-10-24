import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QComboBox, QGroupBox, QPushButton, QProgressBar,
    QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from dotenv import load_dotenv
from utils.git_utils import GithubActionManager, GitCommands
            
class MainWindow(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.language_colors = {
            'Java': '#f89820',
            'Python': '#3572A5',
            'JavaScript': '#f1e05a',
            'TypeScript': '#2b7489',
            'HTML': '#e34c26',
            'CSS': '#563d7c',
            'Go': '#00ADD8',
            'Shell': '#89e051',
            'Dockerfile': '#384d54',
            'Swift': '#ffac45',
            'Objective-C': '#438eff',
            'C': '#555555',
            'Ruby': '#701516',
            # ... add more languages as needed
        }
        self.initUI()

    def initUI(self):
            self.setWindowTitle('Repository Language Breakdown')
            self.setGeometry(100, 100, 1000, 700)
            self.setWindowIcon(QIcon('app_icon.png'))  # Ensure 'app_icon.png' exists

            self.apply_stylesheet()

            # Main layout
            main_layout = QVBoxLayout()

            # Controls layout
            controls_layout = QHBoxLayout()

            # Language filter combo box
            self.language_filter_combo = QComboBox()
            self.language_filter_combo.addItem('Filter by Language')
            self.populate_language_combo()
            self.language_filter_combo.currentIndexChanged.connect(self.populate_table)
            self.language_filter_combo.setToolTip('Filter repositories to display only those that use the selected language.')

            controls_layout.addWidget(QLabel('Filter by Language:'))
            controls_layout.addWidget(self.language_filter_combo)

            # Language sort combo box
            self.language_combo = QComboBox()
            self.language_combo.addItem('Select Language to Sort By')
            self.populate_language_sort_combo()
            self.language_combo.currentIndexChanged.connect(self.sort_table)
            self.language_combo.setToolTip('Select a language to sort repositories by their usage percentage.')

            controls_layout.addWidget(QLabel('Sort by Language:'))
            controls_layout.addWidget(self.language_combo)

            # Add the "Run" button to generate/refresh data
            self.run_button = QPushButton('Run Data Generation')
            self.run_button.clicked.connect(self.run_generate_data)
            controls_layout.addWidget(self.run_button)

            # Add the "Download" button
            self.download_button = QPushButton('Download Selected Repos and count LOC')
            self.download_button.setEnabled(False)  # Initially disabled until selection
            self.download_button.clicked.connect(self.download_selected_repos)
            controls_layout.addWidget(self.download_button)

            main_layout.addLayout(controls_layout)

            # Progress Bar at the bottom
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setAlignment(Qt.AlignCenter)
            self.progress_bar.setValue(0)
            main_layout.addWidget(self.progress_bar)

            # Split the main layout into two parts: left and right
            content_layout = QHBoxLayout()
            main_layout.addLayout(content_layout)

            # Left side: Table with multi-selection enabled
            self.table = QTableWidget()
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(['Repository', 'Languages', 'Total Languages'])
            self.table.setSelectionMode(QAbstractItemView.MultiSelection)  # Enable multi-selection
            self.table.selectionModel().selectionChanged.connect(self.handle_repo_selection)
            self.table.cellClicked.connect(self.display_language_breakdown)
            self.table.setToolTip('Click on a repository to view its language breakdown.')
            self.table.setAlternatingRowColors(True)
            content_layout.addWidget(self.table)

            # Right side: Details and Plot
            right_layout = QVBoxLayout()
            content_layout.addLayout(right_layout)

            # Repository details
            self.details_group = QGroupBox('Repository Details')
            details_layout = QVBoxLayout()
            self.repo_icon_label = QLabel()
            self.repo_details_label = QLabel("Select a repository to see details.")
            self.repo_details_label.setWordWrap(True)
            self.repo_details_label.setOpenExternalLinks(True)
            details_layout.addWidget(self.repo_icon_label)
            details_layout.addWidget(self.repo_details_label)
            self.details_group.setLayout(details_layout)
            right_layout.addWidget(self.details_group)

            # Matplotlib canvas for plotting
            self.figure = plt.figure(figsize=(5, 4))
            self.canvas = FigureCanvas(self.figure)
            right_layout.addWidget(self.canvas)

            # Status bar
            self.status_label = QLabel('')
            main_layout.addWidget(self.status_label)

            self.setLayout(main_layout)

            # Populate the table with repository data
            self.populate_table()
        
    def run_generate_data(self):
        """
        This function is triggered when the "Run Data Generation" button is clicked.
        It runs the generate_data function to refresh the repository data.
        """
        from utils.generate_data import generate_data
        generate_data()  # Run the data generation
        self.refresh_data()

    def refresh_data(self):
        """
        Reload the generated data and refresh the table with updated data.
        """
        from utils.utils import load_json_from_file
        data = load_json_from_file(os.environ.get('DATA_SAVE_PATH'))
        self.data = data
        self.populate_table()  # Refresh the table with new data

    def apply_stylesheet(self):
        style = """
        QWidget {
            background-color: #f0f0f0;
            font-size: 14px;
        }
        QTableWidget {
            background-color: white;
            alternate-background-color: #e9e9e9;
        }
        QHeaderView::section {
            background-color: #d3d3d3;
            padding: 4px;
            border: 1px solid #c0c0c0;
        }
        QComboBox, QPushButton {
            padding: 4px;
        }
        """
        self.setStyleSheet(style)

    def populate_language_combo(self):
        languages = set()
        for repo_data in self.data.values():
            languages.update(repo_data['languages'].keys())
        sorted_languages = sorted(languages)
        self.language_filter_combo.addItems(sorted_languages)

    def populate_language_sort_combo(self):
        languages = set()
        for repo_data in self.data.values():
            languages.update(repo_data['languages'].keys())
        sorted_languages = sorted(languages)
        self.language_combo.addItems(sorted_languages)

    def populate_table(self):
        self.table.setRowCount(0)  # Clear existing data

        # Get selected language filter
        filter_language = self.language_filter_combo.currentText()
        if filter_language == 'Filter by Language':
            filter_language = None

        for repo_name, repo_data in self.data.items():
            if filter_language and filter_language not in repo_data['languages']:
                continue  # Skip repositories that don't use the selected language

            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Repository name
            self.table.setItem(row_position, 0, QTableWidgetItem(repo_name))

            # Languages (displayed as a comma-separated string)
            languages = ', '.join(repo_data['languages'].keys())
            self.table.setItem(row_position, 1, QTableWidgetItem(languages))

            # Total number of languages
            total_languages = str(len(repo_data['languages']))
            self.table.setItem(row_position, 2, QTableWidgetItem(total_languages))

        self.table.resizeColumnsToContents()

        if filter_language:
            self.status_label.setText(f'Repositories filtered by {filter_language}')
        else:
            self.status_label.setText('All repositories displayed')

    def sort_table(self):
        selected_language = self.language_combo.currentText()
        if selected_language == 'Select Language to Sort By':
            selected_language = None

        filter_language = self.language_filter_combo.currentText()
        if filter_language == 'Filter by Language':
            filter_language = None

        # Prepare data for sorting
        repo_list = []
        for repo_name, repo_data in self.data.items():
            if filter_language and filter_language not in repo_data['languages']:
                continue  # Skip repositories that don't use the filter language

            percentage = repo_data['languages'].get(selected_language, 0) if selected_language else 0
            repo_list.append((repo_name, repo_data, percentage))

        # Sort repositories based on the selected language percentage
        if selected_language:
            sorted_repos = sorted(repo_list, key=lambda x: x[2], reverse=True)
            self.status_label.setText(f'Repositories sorted by {selected_language}')
        else:
            sorted_repos = repo_list  # No sorting if no language selected
            self.status_label.setText('Repositories displayed without sorting')

        # Update table with sorted data
        self.table.setRowCount(0)
        for repo_name, repo_data, percentage in sorted_repos:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            # Repository name
            item = QTableWidgetItem(repo_name)
            if percentage > 0:
                item.setData(Qt.UserRole, percentage)
            self.table.setItem(row_position, 0, item)

            # Languages
            languages = ', '.join(repo_data['languages'].keys())
            self.table.setItem(row_position, 1, QTableWidgetItem(languages))

            # Total number of languages
            total_languages = str(len(repo_data['languages']))
            self.table.setItem(row_position, 2, QTableWidgetItem(total_languages))

        self.table.resizeColumnsToContents()

    def display_language_breakdown(self, row, column):
        repo_name_item = self.table.item(row, 0)
        if repo_name_item:
            repo_name = repo_name_item.text()
            repo_data = self.data.get(repo_name)
            if repo_data:
                self.update_repository_details(repo_name, repo_data)
                if repo_data['languages']:
                    self.plot_language_breakdown(repo_name, repo_data['languages'])
                else:
                    self.figure.clear()
                    self.canvas.draw()
                self.status_label.setText(f'Selected Repository: {repo_name}')

    def update_repository_details(self, repo_name, repo_data):
        details_html = f"""
        <h3>{repo_name}</h3>
        <p><b>Public SCM:</b> {repo_data['public_scm']}</p>
        <p><b>Public URL:</b> <a href="{repo_data['public_url']}">{repo_data['public_url']}</a></p>
        <p><b>Last Commit Date:</b> {repo_data['last_commit_date']}</p>
        """

        # if repo_data['internal_urls']:
        #     details_html += "<p><b>Internal URLs:</b><br>" + "<br>".join(repo_data['internal_urls']) + "</p>"

        # Attempt to load repository icon
        icon_path = f'icons/{repo_name}.png'  # Ensure icons are stored in 'icons' directory
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.repo_icon_label.setPixmap(pixmap)
        else:
            # If no icon, clear any existing pixmap
            self.repo_icon_label.clear()

        self.repo_details_label.setText(details_html)
        self.repo_details_label.setOpenExternalLinks(True)

    def plot_language_breakdown(self, repo_name, languages):
        self.figure.clear()
        
        # Increase figure size to accommodate longer labels
        self.figure.set_size_inches(5, 4)  # Adjust width and height as needed

        ax = self.figure.add_subplot(111)

        labels = list(languages.keys())
        sizes = list(languages.values())

        # Sort languages and sizes in descending order
        labels_sizes = sorted(zip(labels, sizes), key=lambda x: x[1], reverse=True)
        labels, sizes = zip(*labels_sizes)

        # Get colors for each language
        colors = [self.language_colors.get(lang, 'grey') for lang in labels]

        # Create a bar chart
        bars = ax.barh(labels, sizes, color=colors)
        ax.set_xlabel('Percentage')
        ax.set_title(f'Language Breakdown for {repo_name}')
        ax.invert_yaxis()  # Highest values on top

        # Adjust the x-axis limit to ensure text fits
        max_size = max(sizes)
        x_limit = max_size  # Add 15% margin to the maximum value
        ax.set_xlim(0, x_limit)

        # Reduce font size of y-axis labels if necessary
        ax.tick_params(axis='y', labelsize=10)  # Adjust fontsize as needed

        # Adjust the left margin to accommodate long labels
        self.figure.subplots_adjust(left=0.275)  # Increase the left margin

        # Alternatively, use tight_layout()
        self.figure.tight_layout()

        # Add percentage labels next to the bars
        for i, (bar, size) in enumerate(zip(bars, sizes)):
            bar_width = bar.get_width()
            label_x_pos = bar_width + (max_size * 0.02)  # Position label slightly after the bar

            # Check if label would go beyond the axis limit
            if label_x_pos >= x_limit:
                # Position label inside the bar
                label_x_pos = bar_width - (max_size * 0.02)
                label_color = 'white'
                alignment = 'right'
            else:
                # Position label outside the bar
                label_color = 'black'
                alignment = 'left'

            # Add the text label
            ax.text(
                label_x_pos,
                bar.get_y() + bar.get_height() / 2,
                f"{size}%",
                va='center',
                ha=alignment,
                color=label_color,
                fontsize=10
            )

        self.canvas.draw()


    def handle_repo_selection(self):
            """Handle multi-selection of repositories."""
            selected_items = self.table.selectedItems()
            selected_repos = set()
            self.selected_repo_urls = []

            # Get the selected repositories based on the rows selected
            for item in selected_items:
                row = item.row()
                repo_name_item = self.table.item(row, 0)  # Get the repository name from the first column
                if repo_name_item:
                    repo_name = repo_name_item.text()
                    if repo_name not in selected_repos:
                        repo_data = self.data.get(repo_name)
                        if repo_data:
                            self.selected_repo_urls.append(repo_data['public_git_url'])  # Store the Git URL
                            selected_repos.add(repo_name) 

            if self.selected_repo_urls:
                self.download_button.setEnabled(True)  
                self.status_label.setText(f"{len(self.selected_repo_urls)} repositories selected.")
            else:
                self.download_button.setEnabled(False)  
     
    def download_selected_repos(self):
        """Download the selected repositories using git_repo_download."""
        if self.selected_repo_urls:
            for repo_url in self.selected_repo_urls:
                self.git_repo_download(repo_url)
        else:
            self.status_label.setText("No repositories selected for download.")

    def git_repo_download(self, repo_url):
        """Download the repository using git clone."""
        git_actions = GithubActionManager()
        results = git_actions.git_run_commands(GitCommands.CLONE, working_directory=os.environ.get("GIT_CLONE_FOLDER_PATH") ,git_url=repo_url)
        a=1