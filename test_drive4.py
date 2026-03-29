import sys
sys.path.append('c:\\Users\\nacfz\\Desktop\\조합장검색기_Streamlit')
from 조합장_web import load_service_account_info, build, service_account, FOLDER_ID

try:
    creds_info = load_service_account_info()
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds)
    response = service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="nextPageToken, files(id, name)",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    print("Success: ", response)
except Exception as e:
    print("Error: ", e)
