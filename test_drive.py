import sys
sys.path.append('c:\\Users\\nacfz\\Desktop\\조합장검색기_Streamlit')
from 조합장_web import load_service_account_info, list_drive_photos, FOLDER_ID

photos = list_drive_photos(FOLDER_ID)
found = [p for p in photos if '128' in p['name']]
print(f"Total photos in folder {FOLDER_ID}: {len(photos)}")
print(f"Found matches for '128': {found}")
