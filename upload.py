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

# --- Setup session ---
video_size = os.path.getsize(local_file)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.tiktok.com/upload',
    'Origin': 'https://www.tiktok.com'
})
session.cookies.set('sessionid', session_id, domain='.tiktok.com')
session.cookies.set('sessionid_ss', session_id, domain='.tiktok.com')

# --- Step 1: Get upload signature ---
print("Getting upload signature...")
sign_url = "https://www.tiktok.com/api/v1/web/upload/auth/"
sign_resp = session.get(sign_url)
print("Sign status: " + str(sign_resp.status_code))
print("Sign response: " + sign_resp.text[:300])

# --- Step 2: Initialize upload ---
print("Initializing upload...")
init_url = "https://www.tiktok.com/api/v1/web/upload/init/"
init_payload = {
    "video_size": video_size,
    "part_size": video_size,
    "part_num": 1
}
init_resp = session.post(init_url, json=init_payload)
print("Init status: " + str(init_resp.status_code))
print("Init response: " + init_resp.text[:500])

try:
    init_data = init_resp.json()
    upload_url = (
        init_data.get('data', {}).get('upload_url') or
        init_data.get('upload_url') or
        init_data.get('data', {}).get('url')
    )
    upload_id = (
        init_data.get('data', {}).get('upload_id') or
        init_data.get('upload_id')
    )
    print("Upload URL: " + str(upload_url))
    print("Upload ID: " + str(upload_id))
except Exception as e:
    print("Parse error: " + str(e))
    exit(1)

if not upload_url:
    print("ERROR: No upload URL received.")
    print("Full response: " + init_resp.text)
    exit(1)

# --- Step 3: Upload video ---
print("Uploading video...")
with open(local_file, 'rb') as f:
    video_data = f.read()

upload_resp = session.put(
    upload_url,
    data=video_data,
    headers={
        'Content-Type': 'video/mp4',
        'Content-Length': str(video_size)
    }
)
print("Upload status: " + str(upload_resp.status_code))
print("Upload response: " + upload_resp.text[:300])

# --- Step 4: Publish video ---
if upload_resp.status_code in [200, 201, 204]:
    print("Publishing video...")
    publish_url = "https://www.tiktok.com/api/v1/web/upload/publish/"
    publish_payload = {
        "upload_id": upload_id,
        "text": caption,
        "privacy_level": 0
    }
    publish_resp = session.post(publish_url, json=publish_payload)
    print("Publish status: " + str(publish_resp.status_code))
    print("Publish response: " + publish_resp.text[:300])

    if publish_resp.status_code == 200:
        drive.files().delete(fileId=video_id).execute()
        print("Done! Video posted and deleted from Drive.")
    else:
        print("Publish failed.")
        exit(1)
else:
    print("Upload failed.")
    exit(1)
