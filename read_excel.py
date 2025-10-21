
import pandas as pd

try:
    df = pd.read_excel('C:\\Users\\nacfz\\Desktop\\Python\\조합장 현황(20250728_시트별_차트_비율포함).xlsx', sheet_name=0)
    print("컬럼:", df.columns.tolist())
    print("\n데이터 샘플 (첫 5줄):")
    print(df.head().to_string())
except Exception as e:
    print(f"An error occurred: {e}")


