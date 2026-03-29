import sys
sys.path.append('c:\\Users\\nacfz\\Desktop\\조합장검색기_Streamlit')
from 조합장_web import load_data
df, ts, source, logs = load_data()
print("Data rows:", len(df))
print("Source:", source)
print("Logs:", logs)
