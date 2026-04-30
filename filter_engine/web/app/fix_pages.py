import os

base = r'e:\MEDIA_ANALYSIS_SYSTEM\xhs-crawler\filter_engine\web\app\src\pages'
for fname in ['Page2Layer2.tsx', 'Page3Layer3.tsx', 'Page4Results.tsx']:
    path = os.path.join(base, fname)
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    count = 0
    cut = len(lines)
    for i, l in enumerate(lines):
        if 'const PAGE_SIZE' in l:
            count += 1
            if count == 2:
                cut = i
                break
    print(fname, 'total', len(lines), 'cut at', cut)
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines[:cut])
print('done')
