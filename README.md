# YouTube Downloader

A simple PyQt6-based application for downloading YouTube videos using yt-dlp.

## Features

- Download YouTube videos in different quality options (high, medium, low)
- Extract audio only (mp3 format)
- Select custom download location
- Progress tracking
- Convenient clipboard paste functionality
- Download history panel with format tags
  - Color-coded entries (green for high quality, yellow for medium, red for low, blue for audio)
  - Icons to distinguish between video (🎬) and audio (🎵) downloads
  - Detailed tooltips with information about each download
  - Right-click options to open in Finder or play video
- Thumbnail preview and display
  - Real-time thumbnail preview when entering YouTube URLs
  - Thumbnails automatically downloaded with videos
  - Thumbnails visible in the history panel
  - Select a download from history to view its thumbnail
- Loading indicators for thumbnail fetching

## Requirements

- Python 3.6+
- PyQt6
- yt-dlp

## Installation

1. Clone or download this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python youtube_downloader.py
```

1. Paste a YouTube URL into the input field (you'll see a thumbnail preview)
2. Select the desired format (video quality or audio only)
3. Choose where to save the downloaded file
4. Click "Download"
5. View your download history in the left panel
6. Select items in history to view their thumbnails
7. Right-click on history items to:
   - Open the file location in Finder
   - Play the video with your default media player

## Screenshots

(Screenshots will be added here)

## License

MIT

## Notes

- This application is for personal use only
- Please respect copyright laws and YouTube's terms of service
- Download history is stored in a JSON file (download_history.json) in the application directory
- Thumbnails are saved alongside videos and referenced in the history file
# porygon-yt-dlp
