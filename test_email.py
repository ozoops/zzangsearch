import sys
sys.path.append('c:\\Users\\nacfz\\Desktop\\조합장검색기_Streamlit')
from 조합장_web import load_service_account_info
info = load_service_account_info()
if info:
    print(info.get('client_email'))
else:
    print("NO INFO")
