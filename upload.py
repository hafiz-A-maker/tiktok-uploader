import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from tiktok_uploader.upload import upload_video

# --- CONFIG ---
FOLDER_NAME = "TIKTOK_UPLOADS"
COOKIES_FILE = "cookies.txt"
CREDENTIALS_FILE = "credentials.json"

# --- Connect to Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_FILE, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

# --- Find the TIKTOK_UPLOADS folder ---
folder_query = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
folders = drive.files().list(q=folder_query).execute().get('files', [])
if not folders:
    print("Folder not found. Exiting.")
    exit()
folder_id = folders[0]['id']

# --- Find a video file inside the folder ---
video_query = f"'{folder_id}' in parents and mimeType contains 'video/'"
videos = drive.files().list(q=video_query).execute().get('files', [])
if not videos:
    print("No videos found. Exiting.")
    exit()

video = videos[0]
video_id = video['id']
video_name = video['name']
local_file = "video_to_upload.mp4"

# --- Download the video ---
print(f"Downloading: {video_name}")
request = drive.files().get_media(fileId=video_id)
with open(local_file, 'wb') as f:
    downloader = MediaIoBaseDownload(f, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

# --- Get caption from filename (before the | symbol) ---
caption = video_name.split('|')[0].strip().replace('.mp4', '')
if not caption:
    caption = "New video #fyp"

# --- Upload to TikTok ---
print(f"Uploading to TikTok with caption: {caption}")
upload_video(COOKIES_FILE, local_file, caption)

# --- Delete from Drive after upload ---
drive.files().delete(fileId=video_id).execute()
print("Done! Video deleted from Drive.")
