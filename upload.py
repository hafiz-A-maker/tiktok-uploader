import os
import io
import json
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# --- Read secrets ---
credentials_content = os.environ.get('GOOGLE_CREDENTIALS')
base_dir = os.path.dirname(os.path.abspath(__file__))
credentials_path = os.path.join(base_dir, 'credentials.json')
local_file = os.path.join(base_dir, 'video_to_upload.mp4')

with open(credentials_path, 'w') as f:
    f.write(credentials_content)

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

# --- Upload to TikTok via API ---
ACCESS_TOKEN = os.environ.get('TIKTOK_ACCESS_TOKEN')

print(f"Uploading: {caption}")

# Step 1: Initialize upload
init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}
video_size = os.path.getsize(local_file)
init_data = {
    "post_info": {
        "title": caption,
        "privacy_level": "SELF_ONLY",
        "disable_duet": False,
        "disable_comment": False,
        "disable_stitch": False
    },
    "source_info": {
        "source": "FILE_UPLOAD",
        "video_size": video_size,
        "chunk_size": video_size,
        "total_chunk_count": 1
    }
}
init_resp = requests.post(init_url, headers=headers, json=init_data)
init_json = init_resp.json()
print("Init response:", init_json)

publish_id = init_json['data']['publish_id']
upload_url = init_json['data']['upload_url']

# Step 2: Upload video chunk
with open(local_file, 'rb') as f:
    video_data = f.read()

upload_headers = {
    "Content-Type": "video/mp4",
    "Content-Range": f"bytes 0-{video_size-1}/{video_size}",
    "Content-Length": str(video_size)
}
upload_resp = requests.put(upload_url, headers=upload_headers, data=video_data)
print("Upload status:", upload_resp.status_code)

if upload_resp.status_code in [200, 201]:
    drive.files().delete(fileId=video_id).execute()
    print("Done! Video uploaded and deleted from Drive.")
else:
    print("Upload failed:", upload_resp.text)
