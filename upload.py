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
session_id = os.environ.get('TIKTOK_SESSION_ID')

base_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(base_dir, 'credentials.json')
local_file = os.path.join(base_dir, 'video_to_upload.mp4')

with open(credentials_path, 'w') as f:
    f.write(credentials_content)

print("Files written OK")

# --- Connect to Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    credentials_path, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

# --- Find TIKTOK_UPLOADS folder ---
FOLDER_NAME = "TIKTOK_UPLOADS"
folder_query = "name='TIKTOK_UPLOADS' and mimeType='application/vnd.google-apps.folder'"
folders = drive.files().list(q=folder_query).execute().get('files', [])
if not folders:
    print("Folder not found.")
    exit()
folder_id = folders[0]['id']

# --- Find a video ---
video_query = "'" + folder_id + "' in parents and mimeType contains 'video/'"
videos = drive.files().list(q=video_query).execute().get('files', [])
if not videos:
    print("No videos found.")
    exit()

video = videos[0]
video_id = video['id']
video_name = video['name']

# --- Download video ---
print("Downloading: " + video_name)
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

# --- Change to base directory ---
os.chdir(base_dir)

print("video exists: " + str(os.path.exists('video_to_upload.mp4')))
print("session_id set: " + str(session_id is not None))
print("Uploading: " + caption)

# --- Upload to TikTok using session ID directly ---
auth = AuthBackend(cookies_list=[{
    'name': 'sessionid',
    'value': session_id,
    'domain': '.tiktok.com',
    'path': '/'
}])

upload_videos(
    videos=[{'path': 'video_to_upload.mp4', 'description': caption}],
    auth=auth,
    headless=True
)

# --- Delete from Drive ---
drive.files().delete(fileId=video_id).execute()
print("Done! Video deleted from Drive.")