import sys
sys.path.append('c:\\Users\\nacfz\\Desktop\\조합장검색기_Streamlit')
from 조합장_web import load_service_account_info, build, service_account, FOLDER_ID

try:
    creds_info = load_service_account_info()
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds)
    response = service.files().get(
        fileId=FOLDER_ID,
        fields="id, name, shared, permissions"
    ).execute()
    print("Folder info: ", response)
except Exception as e:
    print("Error getting folder: ", e)
