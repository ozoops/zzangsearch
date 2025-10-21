
import pandas as pd
import os
import glob

# Paths
excel_path = r'C:\Users\nacfz\Desktop\Python\조합장 현황(20250728_시트별_차트_비율포함).xlsx'
photo_dir = r'C:\Users\nacfz\Desktop\Python\photo'

# --- Analysis logic to find perfect matches ---
try:
    df = pd.read_excel(excel_path, sheet_name=0)
except FileNotFoundError:
    print(f"엑셀 파일을 찾을 수 없습니다: {excel_path}")
    exit()

df = df[pd.notna(df['성명']) & pd.notna(df['순번'])].copy()
df['순번'] = df['순번'].astype(int)
df['성명'] = df['성명'].astype(str).str.strip()

all_photos = glob.glob(os.path.join(photo_dir, '*.jpg'))
photo_map = {os.path.splitext(os.path.basename(p))[0]: p for p in all_photos}

perfect_matches = []
excel_names = df['성명'].unique()

for name in excel_names:
    rows_for_name = df[df['성명'] == name]
    seq_numbers = rows_for_name['순번'].tolist()
    matching_files = sorted([fname for fname in photo_map.keys() if fname == name])

    if len(seq_numbers) == 1 and len(matching_files) == 1:
        seq = seq_numbers[0]
        original_basename = matching_files[0]
        original_path = photo_map[original_basename]
        new_filename = f"{seq}.jpg"
        new_filepath = os.path.join(photo_dir, new_filename)
        perfect_matches.append({
            'original_path': original_path,
            'new_path': new_filepath,
            'original_name': os.path.basename(original_path),
            'new_name': new_filename
        })

# --- Renaming logic ---
renamed_count = 0
error_count = 0

print(f"총 {len(perfect_matches)}개의 파일 이름 변경을 시작합니다...")

for match in perfect_matches:
    try:
        if os.path.exists(match['new_path']):
            print(f"경고: '{match['new_name']}' 파일이 이미 존재하여 건너뜁니다. (원본: '{match['original_name']}')")
            error_count += 1
            continue

        os.rename(match['original_path'], match['new_path'])
        renamed_count += 1
    except Exception as e:
        print(f"오류: '{match['original_name']}' 이름 변경 실패 - {e}")
        error_count += 1

print("\n--- 작업 완료 ---")
print(f"성공: {renamed_count}개")
print(f"실패/건너뜀: {error_count}개")
