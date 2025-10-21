
import pandas as pd
import os
import glob

# Paths
excel_path = r'C:\Users\nacfz\Desktop\Python\조합장 현황(20250728_시트별_차트_비율포함).xlsx'
photo_dir = r'C:\Users\nacfz\Desktop\Python\photo'

# 1. Read Excel
try:
    df = pd.read_excel(excel_path, sheet_name=0)
except FileNotFoundError:
    print(f"엑셀 파일을 찾을 수 없습니다: {excel_path}")
    exit()

# Ensure '성명' and '순번' are clean
df = df[pd.notna(df['성명']) & pd.notna(df['순번'])].copy()
df['순번'] = df['순번'].astype(int)
df['성명'] = df['성명'].astype(str).str.strip()

# 2. Get all photo files
all_photos = glob.glob(os.path.join(photo_dir, '*.jpg'))
photo_map = {os.path.splitext(os.path.basename(p))[0]: p for p in all_photos}

# 3. Analyze and categorize
perfect_matches = []
ambiguous_matches = []
no_match_in_photos = []
processed_photo_files = set()

excel_names = df['성명'].unique()

for name in excel_names:
    # Find all rows in Excel for this name
    rows_for_name = df[df['성명'] == name]
    seq_numbers = rows_for_name['순번'].tolist()

    # Find all matching files in the photo directory
    # This handles '김경식', '김경식1', '김경식_1' etc.
    matching_files = sorted([fname for fname in photo_map.keys() if fname == name])

    if len(seq_numbers) == 1 and len(matching_files) == 1:
        # Perfect 1:1 match
        seq = seq_numbers[0]
        original_basename = matching_files[0]
        original_path = photo_map[original_basename]
        new_filename = f"{seq}.jpg"
        perfect_matches.append({'순번': seq, '성명': name, '원본파일': os.path.basename(original_path), '새파일': new_filename})
        processed_photo_files.add(original_basename)

    elif len(seq_numbers) > 0 and len(matching_files) > 0:
        # Ambiguous cases (e.g., 2 Excel entries, 2 files)
        ambiguous_matches.append({
            '성명': name,
            '엑셀 순번': seq_numbers,
            '매칭 파일': [os.path.basename(photo_map[f]) for f in matching_files]
        })
        for f in matching_files:
            processed_photo_files.add(f)
    
    elif len(seq_numbers) > 0 and len(matching_files) == 0:
        # Name is in Excel, but no photo found
        for seq in seq_numbers:
            no_match_in_photos.append({'순번': seq, '성명': name})


# 4. Find orphan files (photos without an entry in Excel)
all_photo_basenames = set(photo_map.keys())
orphan_files = all_photo_basenames - processed_photo_files
orphan_file_paths = [os.path.basename(photo_map[f]) for f in orphan_files]

# 5. Report results
print("---" + " 파일명 변경 분석 결과 " + "---")
print(f"\n[1. 이름 변경 가능] 1:1로 매칭되는 파일: {len(perfect_matches)}개")
if perfect_matches:
    # Sort by '순번' for cleaner display
    perfect_matches.sort(key=lambda x: x['순번'])
    print("   (예시 5개)", perfect_matches[:5])

print(f"\n[2. 확인 필요] 동명이인 또는 중복 파일 의심: {len(ambiguous_matches)}건")
if ambiguous_matches:
    print("   (예시 5개)", ambiguous_matches[:5])

print(f"\n[3. 확인 필요] 엑셀에 있으나, 사진 파일이 없는 경우: {len(no_match_in_photos)}건")
if no_match_in_photos:
    no_match_in_photos.sort(key=lambda x: x['순번'])
    print("   (예시 5개)", no_match_in_photos[:5])

print(f"\n[4. 확인 필요] 엑셀에 없어 처리되지 않은 사진 파일: {len(orphan_file_paths)}개")
if orphan_file_paths:
    print("   (예시 5개)", sorted(orphan_file_paths)[:5])

print("\n---" + " 다음 단계 제안 " + "---")
print("분석 결과를 확인해주세요.")
print("1. '[1. 이름 변경 가능]' 목록에 있는 파일들의 이름을 실제로 변경할까요?")
print("2. '[2. 확인 필요]' 목록의 동명이인/중복 의심 파일은 어떻게 처리할지 알려주세요.")
