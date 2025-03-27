import sys
import os
import subprocess
import json
import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog,
    QProgressBar, QMessageBox, QGroupBox, QSplitter, QListWidget,
    QListWidgetItem, QScrollArea, QFrame, QMenu
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSize, QUrl, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont, QPixmap, QImage, QMovie
import urllib.request
import webbrowser

class DownloadThread(QThread):
    """Thread for running yt-dlp without freezing the UI"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str, str, str, str)  # success, message, title, format_option, thumbnail_path
    thumbnail_ready = pyqtSignal(str)  # thumbnail path
    
    def __init__(self, url, output_path, format_option):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.format_option = format_option
        self.title = ""
        self.thumbnail_path = ""
        
    def run(self):
        try:
            # Build the yt-dlp command based on the selected format
            cmd = ['yt-dlp']
            
            if self.format_option == "High Quality Video (mp4)":
                cmd.extend(['-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'])
            elif self.format_option == "Medium Quality Video (mp4)":
                cmd.extend(['-f', 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]'])
            elif self.format_option == "Low Quality Video (mp4)":
                cmd.extend(['-f', 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]'])
            elif self.format_option == "Audio Only (mp3)":
                cmd.extend(['-x', '--audio-format', 'mp3'])
            
            # Get title and thumbnail info first
            title_cmd = ['yt-dlp', '--get-title', self.url]
            title_process = subprocess.run(title_cmd, capture_output=True, text=True)
            if title_process.returncode == 0:
                self.title = title_process.stdout.strip()
                
            # Get thumbnail URL
            thumbnail_cmd = ['yt-dlp', '--get-thumbnail', self.url]
            thumbnail_process = subprocess.run(thumbnail_cmd, capture_output=True, text=True)
            if thumbnail_process.returncode == 0:
                thumbnail_url = thumbnail_process.stdout.strip()
                # Download the thumbnail
                thumbnail_filename = os.path.join(self.output_path, f"{self.title}_thumbnail.jpg")
                try:
                    urllib.request.urlretrieve(thumbnail_url, thumbnail_filename)
                    self.thumbnail_path = thumbnail_filename
                    # Signal that the thumbnail is ready
                    self.thumbnail_ready.emit(self.thumbnail_path)
                except Exception as e:
                    print(f"Error downloading thumbnail: {e}")
            
            # Also download thumbnail with yt-dlp as backup
            cmd.append('--write-thumbnail')
            
            # Add output path
            cmd.extend(['-o', f'{self.output_path}/%(title)s.%(ext)s'])
            
            # Add URL
            cmd.append(self.url)
            
            # Execute the command
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream the output
            for line in process.stdout:
                self.progress.emit(line.strip())
                
                # Check if thumbnail is written in this line
                if "[info] Writing thumbnail" in line and not self.thumbnail_path:
                    parts = line.split("Writing thumbnail to: ")
                    if len(parts) > 1:
                        self.thumbnail_path = parts[1].strip()
                        self.thumbnail_ready.emit(self.thumbnail_path)
            
            # Wait for the process to complete
            process.wait()
            
            if process.returncode == 0:
                self.finished.emit(True, "Download completed successfully!", self.title, self.format_option, self.thumbnail_path)
            else:
                self.finished.emit(False, f"Download failed with error code {process.returncode}", "", "", "")
                
        except Exception as e:
            self.finished.emit(False, f"An error occurred: {str(e)}", "", "", "")


class ThumbnailWidget(QWidget):
    """Widget to display a thumbnail with a title"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Create frame for the image
        self.image_frame = QFrame()
        self.image_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.image_frame.setMinimumSize(200, 150)
        self.image_frame.setMaximumSize(300, 200)
        
        # Layout for the image frame
        self.image_layout = QVBoxLayout(self.image_frame)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        
        # Image label inside frame
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        self.image_layout.addWidget(self.image_label)
        
        # Loading spinner label
        self.loading_label = QLabel()
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Create a loading spinner using QMovie
        self.spinner = None  # Will be initialized in show_loading
        self.loading_label.setMinimumSize(200, 150)
        self.loading_label.setMaximumSize(300, 200)
        self.image_layout.addWidget(self.loading_label)
        self.loading_label.hide()  # Hide by default
        
        # Title label
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        
        # Add widgets to main layout
        self.layout.addWidget(self.image_frame)
        self.layout.addWidget(self.title_label)
        
        # Initialize state
        self.is_loading = False
        
    def set_image(self, image_path):
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.hide_loading()
                self.image_label.setPixmap(pixmap)
                self.image_label.show()
                return True
        return False
    
    def show_loading(self):
        """Show the loading spinner"""
        self.is_loading = True
        self.image_label.hide()
        
        # Create spinner if it doesn't exist
        if not self.spinner:
            # Create a text-based loading indicator if QMovie isn't working well
            self.loading_label.setText("Loading thumbnail...")
            self.loading_label.setStyleSheet("background-color: #f0f0f0; color: #333; font-weight: bold;")

            # Alternative: use a timer to show animated dots
            self.dot_count = 0
            self.dot_timer = QTimer()
            self.dot_timer.timeout.connect(self.update_loading_text)
            self.dot_timer.start(500)  # Update every 500ms
        
        self.loading_label.show()
    
    def update_loading_text(self):
        """Update the loading text animation"""
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        self.loading_label.setText(f"Loading thumbnail{dots}")
    
    def hide_loading(self):
        """Hide the loading spinner"""
        self.is_loading = False
        self.loading_label.hide()
        
        # Stop the timer if it's running
        if hasattr(self, 'dot_timer') and self.dot_timer.isActive():
            self.dot_timer.stop()
        
    def set_title(self, title):
        self.title_label.setText(title)
        
    def clear(self):
        """Clear the thumbnail and title"""
        self.image_label.clear()
        self.title_label.clear()
        self.hide_loading()


class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.json")
        self.download_history = []
        self.load_history()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Porygon")
        self.setMinimumSize(900, 500)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create history panel
        self.history_panel = QWidget()
        history_layout = QVBoxLayout(self.history_panel)
        
        history_label = QLabel("Download History")
        history_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        history_layout.addWidget(history_label)
        
        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        self.history_list.setMinimumWidth(250)
        self.history_list.currentRowChanged.connect(self.display_selected_thumbnail)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self.show_history_context_menu)
        self.history_list.setStyleSheet("background-color: #242424;")  # Light gray
        history_layout.addWidget(self.history_list)
        
        # Add thumbnail display area
        self.thumbnail_widget = ThumbnailWidget()
        history_layout.addWidget(self.thumbnail_widget)
        
        # Populate history list
        self.update_history_list()
        
        # Create the main content widget and layout
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        
        # URL input section
        url_group = QGroupBox("Video URL")
        url_layout = QVBoxLayout(url_group)
        
        url_input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube URL here...")
        self.url_input.textChanged.connect(self.on_url_changed)
        url_input_layout.addWidget(self.url_input)
        
        self.paste_button = QPushButton("Paste")
        self.paste_button.clicked.connect(self.paste_url)
        url_input_layout.addWidget(self.paste_button)
        
        url_layout.addLayout(url_input_layout)
        
        # Add URL preview thumbnail
        self.preview_thumbnail = ThumbnailWidget()
        url_layout.addWidget(self.preview_thumbnail)
        
        main_layout.addWidget(url_group)
        
        # Download options section
        options_group = QGroupBox("Download Options")
        options_layout = QVBoxLayout(options_group)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "High Quality Video (mp4)",
            "Medium Quality Video (mp4)",
            "Low Quality Video (mp4)",
            "Audio Only (mp3)"
        ])
        format_layout.addWidget(self.format_combo)
        options_layout.addLayout(format_layout)
        
        # Output folder selection
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Save to:"))
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        self.output_path.setText(os.path.expanduser("~/Downloads"))
        output_layout.addWidget(self.output_path)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        output_layout.addWidget(self.browse_button)
        
        options_layout.addLayout(output_layout)
        main_layout.addWidget(options_group)
        
        # Progress information
        self.log_output = QLineEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Download progress will appear here...")
        main_layout.addWidget(self.log_output)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Download button
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self.start_download)
        main_layout.addWidget(self.download_button)
        
        # Add widgets to splitter
        self.main_splitter.addWidget(self.history_panel)
        self.main_splitter.addWidget(content_widget)
        
        # Set splitter sizes
        self.main_splitter.setSizes([1, 3])  # 1:3 ratio between history panel and content
        
        # Set the central widget
        self.setCentralWidget(self.main_splitter)
        
        # Initialize thread as None
        self.download_thread = None
        self.preview_thread = None
        
        # Create a timer for URL changes to avoid too many thumbnail fetches
        self.url_timer = QTimer()
        self.url_timer.setSingleShot(True)
        self.url_timer.timeout.connect(self.fetch_delayed_preview)
        self.last_url = ""

    def paste_url(self):
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Download Location", self.output_path.text()
        )
        if folder:
            self.output_path.setText(folder)
            
    def on_url_changed(self, url):
        """When URL changes, schedule a thumbnail fetch with a delay"""
        url = url.strip()
        if url and ("youtube.com" in url or "youtu.be" in url) and url != self.last_url:
            self.last_url = url
            # Show loading immediately
            self.preview_thumbnail.clear()
            self.preview_thumbnail.show_loading()
            # Start a timer to fetch the preview after a delay
            self.url_timer.start(800)  # 800ms delay
    
    def fetch_delayed_preview(self):
        """Fetch thumbnail preview after the delay"""
        url = self.url_input.text().strip()
        if url and ("youtube.com" in url or "youtu.be" in url):
            self.fetch_preview(url)
    
    def fetch_preview(self, url):
        """Fetch thumbnail preview for the URL"""
        if self.preview_thread and self.preview_thread.isRunning():
            # Cancel any existing preview thread
            self.preview_thread.terminate()
            self.preview_thread.wait()
            
        # Create a download thread just for thumbnail and title
        self.preview_thread = DownloadThread(url, os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp"), "")
        self.preview_thread.thumbnail_ready.connect(self.update_preview_thumbnail)
        self.preview_thread.start()
    
    def update_preview_thumbnail(self, thumbnail_path):
        """Update the preview thumbnail when available"""
        if thumbnail_path and os.path.exists(thumbnail_path):
            success = self.preview_thumbnail.set_image(thumbnail_path)
            if success:
                # Get title using yt-dlp
                try:
                    title_cmd = ['yt-dlp', '--get-title', self.url_input.text().strip()]
                    title_process = subprocess.run(title_cmd, capture_output=True, text=True)
                    if title_process.returncode == 0:
                        title = title_process.stdout.strip()
                        self.preview_thumbnail.set_title(title)
                except Exception as e:
                    print(f"Error getting title: {e}")
            
    def start_download(self):
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a YouTube URL")
            return
            
        output_path = self.output_path.text()
        format_option = self.format_combo.currentText()
        
        # Disable the download button while download is in progress
        self.download_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Show loading in the thumbnail widget
        self.thumbnail_widget.clear()
        self.thumbnail_widget.show_loading()
        
        # Create and start the download thread
        self.download_thread = DownloadThread(url, output_path, format_option)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.thumbnail_ready.connect(self.update_current_thumbnail)
        self.download_thread.start()
    
    def update_current_thumbnail(self, thumbnail_path):
        """Update the current thumbnail display during download"""
        if thumbnail_path and os.path.exists(thumbnail_path):
            self.thumbnail_widget.set_image(thumbnail_path)
            if self.download_thread and hasattr(self.download_thread, 'title') and self.download_thread.title:
                self.thumbnail_widget.set_title(self.download_thread.title)
        
    def update_progress(self, message):
        self.log_output.setText(message)
        
        # Try to extract progress percentage if available
        if '[download]' in message and '%' in message:
            try:
                percent_str = message.split('%')[0].split()[-1]
                percent = float(percent_str)
                self.progress_bar.setValue(int(percent))
            except (ValueError, IndexError):
                pass
        
    def download_finished(self, success, message, title, format_option, thumbnail_path):
        self.download_button.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.progress_bar.setValue(100)
            
            # Add to download history
            download_info = {
                "title": title if title else "Unknown Title",
                "url": self.url_input.text().strip(),
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "format": format_option,
                "path": self.output_path.text(),
                "thumbnail": thumbnail_path if os.path.exists(thumbnail_path) else ""
            }
            self.download_history.append(download_info)
            self.save_history()
            self.update_history_list()
        else:
            QMessageBox.critical(self, "Error", message)
            self.thumbnail_widget.hide_loading()
            
        # Clean up the thread
        self.download_thread = None
        
    def load_history(self):
        """Load download history from JSON file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.download_history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            self.download_history = []
            
    def save_history(self):
        """Save download history to JSON file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.download_history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
            
    def update_history_list(self):
        """Update the history list widget with download history"""
        self.history_list.clear()
        
        # Add items in reverse order (newest first)
        for item in reversed(self.download_history):
            list_item = QListWidgetItem(f"{item['title']}")
            
            # Add format tag as tooltip
            list_item.setToolTip(f"URL: {item['url']}\nDate: {item['date']}\nFormat: {item['format']}\nPath: {item['path']}")
            
            # Store thumbnail path as user data
            list_item.setData(Qt.ItemDataRole.UserRole, item.get('thumbnail', ''))
            
            # Set background color based on format
            if "High Quality" in item['format']:
                list_item.setText(f"🎬 {item['title']}")
            elif "Medium Quality" in item['format']:
                list_item.setText(f"🎬 {item['title']}")
            elif "Low Quality" in item['format']:
                list_item.setText(f"🎬 {item['title']}")
            elif "Audio Only" in item['format']:
                list_item.setText(f"🎵 {item['title']}")
                
            self.history_list.addItem(list_item)
            
    def display_selected_thumbnail(self, row):
        """Display the thumbnail for the selected history item"""
        if row >= 0:
            item = self.history_list.item(row)
            thumbnail_path = item.data(Qt.ItemDataRole.UserRole)
            title = item.text()
            
            # Show loading first
            self.thumbnail_widget.clear()
            self.thumbnail_widget.show_loading()
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                self.thumbnail_widget.set_image(thumbnail_path)
                self.thumbnail_widget.set_title(title)
            else:
                # Try to get thumbnail from URL if we don't have one saved
                try:
                    for history_item in reversed(self.download_history):
                        if history_item['title'] in title:
                            url = history_item['url']
                            self.fetch_thumbnail_for_history(url, row)
                            break
                except Exception as e:
                    print(f"Error fetching history thumbnail: {e}")
                    self.thumbnail_widget.hide_loading()
    
    def fetch_thumbnail_for_history(self, url, row):
        """Fetch thumbnail for a history item that doesn't have one"""
        try:
            thumbnail_cmd = ['yt-dlp', '--get-thumbnail', url]
            thumbnail_process = subprocess.run(thumbnail_cmd, capture_output=True, text=True)
            if thumbnail_process.returncode == 0:
                thumbnail_url = thumbnail_process.stdout.strip()
                # Download the thumbnail
                temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
                os.makedirs(temp_dir, exist_ok=True)
                thumbnail_filename = os.path.join(temp_dir, f"history_thumbnail_{row}.jpg")
                urllib.request.urlretrieve(thumbnail_url, thumbnail_filename)
                
                # Update the item and display
                item = self.history_list.item(row)
                item.setData(Qt.ItemDataRole.UserRole, thumbnail_filename)
                self.thumbnail_widget.set_image(thumbnail_filename)
                self.thumbnail_widget.set_title(item.text())
                
                # Update the history record
                if row < len(self.download_history):
                    self.download_history[-(row+1)]['thumbnail'] = thumbnail_filename
                    self.save_history()
            else:
                self.thumbnail_widget.hide_loading()
        except Exception as e:
            print(f"Error fetching thumbnail: {e}")
            self.thumbnail_widget.hide_loading()

    def show_history_context_menu(self, position):
        """Show context menu for history items"""
        # Get the selected item
        selected_indexes = self.history_list.selectedIndexes()
        if not selected_indexes:
            return
            
        # Create menu
        menu = QMenu()
        open_action = menu.addAction("Open in Finder")
        play_action = menu.addAction("Play Video")
        youtube_action = menu.addAction("Open YouTube Link")
        
        # Show menu and get selected action
        action = menu.exec(self.history_list.mapToGlobal(position))
        
        if action == open_action:
            self.open_in_finder(selected_indexes[0].row())
        elif action == play_action:
            self.play_video(selected_indexes[0].row())
        elif action == youtube_action:
            self.open_youtube_link(selected_indexes[0].row())
    
    def open_in_finder(self, row):
        """Open the file location in Finder"""
        try:
            # Get the selected history item
            if row < 0 or row >= len(self.download_history):
                return
                
            history_item = self.download_history[-(row+1)]  # Reverse index
            download_dir = history_item.get('path', '')
            file_title = history_item.get('title', 'video')
            file_format = history_item.get('format', '')
            
            if not download_dir or not os.path.exists(download_dir):
                QMessageBox.warning(self, "Folder Not Found", "The download folder could not be found.")
                return
            
            # Determine the actual file extension based on format
            if "Audio Only" in file_format:
                extension = ".mp3"
            else:
                extension = ".mp4"
            
            # First try the simple case - exact filename.extension
            file_path = os.path.join(download_dir, f"{file_title}{extension}")
            
            # If that doesn't exist, search for a file with similar name
            if not os.path.exists(file_path):
                found = False
                for file in os.listdir(download_dir):
                    file_lower = file.lower()
                    title_lower = file_title.lower()
                    
                    # Check if file contains the title and has the right extension
                    if title_lower in file_lower and (file_lower.endswith('.mp4') or file_lower.endswith('.mp3')):
                        file_path = os.path.join(download_dir, file)
                        found = True
                        break
                
                if not found:
                    # Fall back to opening the directory if file not found
                    QMessageBox.warning(self, "File Not Found", 
                        "Could not locate the specific file. Opening download folder instead.")
                    subprocess.run(['open', download_dir])
                    return
            
            # Open Finder and highlight the specific file
            # The 'open -R' command reveals and highlights the file in Finder on macOS
            subprocess.run(['open', '-R', file_path])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open Finder: {str(e)}")
    
    def play_video(self, row):
        """Play the video using the default application"""
        try:
            # Get the selected history item
            if row < 0 or row >= len(self.download_history):
                return
                
            history_item = self.download_history[-(row+1)]  # Reverse index
            file_path = history_item.get('path', '')
            
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", "The video file could not be found.")
                return
            
            # Determine the actual file to play based on the format
            file_title = history_item.get('title', 'video')
            file_format = history_item.get('format', '')
            
            # Construct probable file name based on format
            if "Audio Only" in file_format:
                extension = ".mp3"
            else:
                extension = ".mp4"
                
            file_to_play = os.path.join(file_path, f"{file_title}{extension}")
            
            # Check if file exists, if not try to find it
            if not os.path.exists(file_to_play):
                # Look for files with similar names in the directory
                for file in os.listdir(file_path):
                    if file_title in file and (file.endswith('.mp4') or file.endswith('.mp3')):
                        file_to_play = os.path.join(file_path, file)
                        break
                        
            if os.path.exists(file_to_play):
                # Open the file with the default application
                if sys.platform == "darwin":  # macOS
                    subprocess.run(['open', file_to_play])
                elif sys.platform == "win32":  # Windows
                    os.startfile(file_to_play)
                else:  # Linux
                    subprocess.run(['xdg-open', file_to_play])
            else:
                QMessageBox.warning(self, "File Not Found", "Could not locate the video file.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not play video: {str(e)}")

    def open_youtube_link(self, row):
        """Open the original YouTube link in a web browser"""
        try:
            # Get the selected history item
            if row < 0 or row >= len(self.download_history):
                return
                
            history_item = self.download_history[-(row+1)]  # Reverse index
            url = history_item.get('url', '')
            
            if not url:
                QMessageBox.warning(self, "URL Not Found", "The YouTube URL is not available.")
                return
            
            # Open the URL in the default web browser
            webbrowser.open(url)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open YouTube link: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloader()
    window.show()
    sys.exit(app.exec()) 