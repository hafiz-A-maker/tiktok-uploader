import os
import io
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from tiktok_uploader.upload import upload_videos
from tiktok_uploader.auth import AuthBackend

# --- Read secrets ---
credentials_content = os.environ.get('GOOGLE_CREDENTIALS')
cookies_content = os.environ.get('TIKTOK_COOKIES')

base_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(base_dir, 'credentials.json')
cookies_path = os.path.join(base_dir, 'cookies.txt')

with open(credentials_path, 'w') as f:
    f.write(credentials_content)

with open(cookies_path, 'w') as f:
    f.write(cookies_content)

print("Files written successfully.")
print("Base dir:", base_dir)

# --- Connect to Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    credentials_path, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

# --- Find TIKTOK_UPLOADS folder ---
FOLDER_NAME = "TIKTOK_UPLOADS"
folder_query = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
folders = drive.files().list(q=folder_query).execute().get('files', [])
if not folders:
    print("Folder not found. Exiting.")
    exit()
folder_id = folders[0]['id']

# --- Find a video ---
video_query = f"'{folder_id}' in parents and mimeType contains 'video/'"
videos = drive.files().list(q=video_query).execute().get('files', [])
if not videos:
    print("No videos found. Exiting.")
    exit()

video = videos[0]
video_id = video['id']
video_name = video['name']

# --- Download video ---
print(f"Downloading: {video_name}")
local_file = os.path.join(base_dir, 'video_to_upload.mp4')
request = drive.files().get_media(fileId=video_id)
with open(local_file, 'wb') as f:
    downloader = MediaIoBaseDownload(f, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
print("Download complete.")

# --- Get caption ---
caption = video_name.split('|')[0].strip().replace('.mp4', '')
if not caption:
    caption = "New video #fyp"

# --- Change to base directory so library finds files easily ---
os.chdir(base_dir)

# --- Confirm files exist ---
print("cookies.txt exists:", os.path.exists('cookies.txt'))
print("video exists:", os.path.exists('video_to_upload.mp4'))

# --- Upload to TikTok ---
print(f"Uploading: {caption}")

auth = AuthBackend(cookies='cookies.txt')

upload_videos(
    videos=[{'path': 'video_to_upload.mp4', 'description': caption}],
    auth=auth,
    headless=True
)

# --- Delete from Drive ---
drive.files().delete(fileId=video_id).execute()
print("Done! Video deleted from Drive.")
