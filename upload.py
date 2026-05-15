import os
import io
import json
import time
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

print("Credentials written OK")
print("Session ID set: " + str(session_id is not None))

# --- Connect to Google Drive ---
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    credentials_path, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

# --- Find TIKTOK_UPLOADS folder ---
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
print("Video size: " + str(os.path.getsize(local_file)) + " bytes")

# --- Get caption ---
caption = video_name.split('|')[0].strip().replace('.mp4', '')
if not caption:
    caption = "New video #fyp"
print("Caption: " + caption)

# --- Upload to TikTok ---
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.tiktok.com/',
    'Cookie': 'sessionid=' + session_id + '; sessionid_ss=' + session_id
}

video_size = os.path.getsize(local_file)

# Step 1: Initialize upload
print("Initializing upload...")
init_url = "https://upload.tiktok.com/api/upload/v1/init/"
init_payload = {
    "source": "pfb",
    "video_size": video_size,
    "part_num": 1,
    "part_size": video_size
}

init_resp = requests.post(init_url, headers=headers, json=init_payload)
print("Init status: " + str(init_resp.status_code))
print("Init response: " + init_resp.text[:300])

try:
    init_data = init_resp.json()
    upload_id = init_data.get('data', {}).get('upload_id') or init_data.get('upload_id')
    upload_url = init_data.get('data', {}).get('upload_url') or init_data.get('upload_url')
except Exception as e:
    print("Failed to parse init response: " + str(e))
    exit(1)

if not upload_url:
    # Try alternative endpoint
    print("Trying alternative upload endpoint...")
    init_url2 = "https://www.tiktok.com/api/v1/upload/auth/"
    init_resp2 = requests.get(init_url2, headers=headers)
    print("Alt init status: " + str(init_resp2.status_code))
    print("Alt init response: " + init_resp2.text[:300])
    exit(1)

# Step 2: Upload video
print("Uploading video...")
with open(local_file, 'rb') as f:
    video_data = f.read()

upload_headers = {
    **headers,
    'Content-Type': 'video/mp4',
    'Content-Length': str(video_size)
}

upload_resp = requests.put(upload_url, headers=upload_headers, data=video_data)
print("Upload status: " + str(upload_resp.status_code))
print("Upload response: " + upload_resp.text[:300])

if upload_resp.status_code in [200, 201, 204]:
    drive.files().delete(fileId=video_id).execute()
    print("Done! Video uploaded and deleted from Drive.")
else:
    print("Upload failed.")
    exit(1)