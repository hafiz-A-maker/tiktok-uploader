import os
import io
import json
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# --- Read secrets ---
credentials_content = os.environ.get('GOOGLE_CREDENTIALS')
session_id = os.environ.get('TIKTOK_SESSION_ID')

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

# --- Upload to TikTok using session ID ---
print(f"Uploading: {caption}")

# Step 1: Initialize upload
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Cookie": f"sessionid={session_id}",
    "Referer": "https://www.tiktok.com/"
}

# Get upload URL
init_url = "https://www.tiktok.com/api/upload/init/"
video_size = os.path.getsize(local_file)

init_payload = {
    "video_size": video_size,
    "last_modified": 1000000,
    "is_h265": 0,
    "web_id": "1234567890"
}

init_resp = requests.post(init_url, headers=headers, json=init_payload)
print("Init response:", init_resp.status_code, init_resp.text[:200])

upload_url = init_resp.json().get('upload_url')
if not upload_url:
    print("Failed to get upload URL. Session ID may be expired.")
    exit()

# Step 2: Upload video
with open(local_file, 'rb') as f:
    video_data = f.read()

upload_headers = {
    **headers,
    "Content-Type": "video/mp4",
    "Content-Length": str(video_size)
}

upload_resp = requests.post(upload_url, headers=upload_headers, data=video_data)
print("Upload response:", upload_resp.status_code)

if upload_resp.status_code == 200:
    drive.files().delete(fileId=video_id).execute()
    print("Done! Video uploaded and deleted from Drive.")
else:
    print("Upload failed:", upload_resp.text[:300])
