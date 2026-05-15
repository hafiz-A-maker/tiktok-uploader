import os
import io
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from tiktok_uploader.upload import upload_video

# --- Read secrets from environment variables ---
cookies_content = os.environ.get('TIKTOK_COOKIES')
credentials_content = os.environ.get('GOOGLE_CREDENTIALS')

# --- Write to files using absolute paths ---
base_dir = os.path.dirname(os.path.abspath(__file__))
cookies_path = os.path.join(base_dir, 'cookies.txt')
credentials_path = os.path.join(base_dir, 'credentials.json')
local_file = os.path.join(base_dir, 'video_to_upload.mp4')

with open(cookies_path, 'w') as f:
    f.write(cookies_content)

with open(credentials_path, 'w') as f:
    f.write(credentials_content)

print("Secrets written to:", base_dir)
print("Cookies path:", cookies_path)

# --- CONFIG ---
FOLDER_NAME = "TIKTOK_UPLOADS"

# --- Connect to Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    credentials_path, scopes=SCOPES)
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

# --- Download the video ---
print(f"Downloading: {video_name}")
request = drive.files().get_media(fileId=video_id)
with open(local_file, 'wb') as f:
    downloader = MediaIoBaseDownload(f, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

print("Download complete.")

# --- Get caption from filename (before the | symbol) ---
caption = video_name.split('|')[0].strip().replace('.mp4', '')
if not caption:
    caption = "New video #fyp"

# --- Upload to TikTok ---
print(f"Uploading to TikTok with caption: {caption}")
upload_video(cookies_path, local_file, caption)

# --- Delete from Drive after upload ---
drive.files().delete(fileId=video_id).execute()
print("Done! Video deleted from Drive.")
