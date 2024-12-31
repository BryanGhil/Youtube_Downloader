from django.http import StreamingHttpResponse
import re  # For filename sanitization
from django.shortcuts import render, redirect
from django.http import Http404
import yt_dlp
import os
import threading
import time
from django.conf import settings
from django.utils.encoding import smart_str

# Function to delete file after a delay (5 minutes)
def delete_file_after_delay(filepath, delay=300):
    time.sleep(delay)
    if os.path.exists(filepath):
        os.remove(filepath)
        print(f"Deleted file: {filepath}")

# Function to sanitize filenames
def sanitize_filename(filename):
    # Remove invalid characters and replace spaces with underscores
    filename = re.sub(r'[\\/:*?"<>|#]+', '', filename)
    filename = filename.replace(' ', '_')
    return filename

# File streaming generator
def file_iterator(filepath, chunk_size=8192):
    with open(filepath, 'rb') as file:
        while chunk := file.read(chunk_size):
            yield chunk

# Render the homepage
def index(request):
    return render(request, 'downloader/index.html')

# Handle video download
def download_video(request):
    if request.method == 'POST':
        youtube_url = request.POST.get('youtube_url')

        if youtube_url:
            # Define the download directory
            download_dir = os.path.join(settings.BASE_DIR, 'downloads')
            os.makedirs(download_dir, exist_ok=True)

            try:
                # yt-dlp options to download video as MP4
                ydl_opts = {
                    'format': 'mp4',
                    'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
                }

                # Download the video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(youtube_url, download=True)
                    original_filepath = ydl.prepare_filename(info)

                # Extract and sanitize the filename
                filename = os.path.basename(original_filepath)
                sanitized_filename = sanitize_filename(filename)
                sanitized_path = os.path.join(download_dir, sanitized_filename)

                # Rename the file to sanitized name
                if original_filepath != sanitized_path:
                    os.rename(original_filepath, sanitized_path)

                # Serve the file as a stream
                response = StreamingHttpResponse(file_iterator(sanitized_path), content_type='video/mp4')
                response['Content-Disposition'] = f'attachment; filename="{smart_str(sanitized_filename)}"'

                # Start the file deletion timer AFTER the response is returned
                threading.Thread(target=delete_file_after_delay, args=(sanitized_path, 300)).start()

                return response

            except Exception as e:
                return Http404(f"Error: {str(e)}")

    return redirect('index')
