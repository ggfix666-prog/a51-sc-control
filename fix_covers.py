import os, subprocess, json, base64
from io import BytesIO
from PIL import Image

SC_DIR = '/sdcard/Music/SoundCloud'
LINKS_FILE = '/sdcard/Download/links.txt'
LIB_PATH = '/sdcard/Download/library.json'

print("=" * 40)
print("ШАГ 1: Скачиваю обложки (15-25 мин)")
print("=" * 40)

with open(LINKS_FILE) as f:
    links = [l.strip() for l in f if l.strip()]

print(f"Ссылок: {len(links)}")
for i, url in enumerate(links, 1):
    try:
        subprocess.run([
            "yt-dlp", "--skip-download", "--write-thumbnail",
            "--convert-thumbnails", "jpg", "--no-warnings", "--no-playlist",
            "-o", f"{SC_DIR}/%(title)s.%(ext)s", url
        ], capture_output=True, timeout=60)
    except: pass
    if i % 20 == 0: print(f"  {i}/{len(links)}")

print("\n" + "=" * 40)
print("ШАГ 2: Обновляю library.json")
print("=" * 40)

def enc(path):
    try:
        img = Image.open(path).convert('RGB')
        img.thumbnail((80, 80))
        buf = BytesIO()
        img.save(buf, 'JPEG', quality=65)
        return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
    except: return ''

with open(LIB_PATH, 'r', encoding='utf-8') as f:
    lib = json.load(f)

tracks = lib.get('tracks', [])
print(f"Треков: {len(tracks)}")
updated = 0
for i, t in enumerate(tracks, 1):
    base = os.path.splitext(t['file'])[0]
    for ext in ['.jpg','.jpeg','.png','.webp']:
        p = os.path.join(SC_DIR, base + ext)
        if os.path.exists(p):
            thumb = enc(p)
            if thumb: t['thumb'] = thumb; updated += 1
            break
    if i % 50 == 0: print(f"  {i}/{len(tracks)}")

with open(LIB_PATH, 'w', encoding='utf-8') as f:
    json.dump(lib, f, ensure_ascii=False)

kb = os.path.getsize(LIB_PATH) // 1024
print(f"\n✅ С обложками: {updated}/{len(tracks)}")
print(f"📁 library.json: {kb} КБ")
print("\nЗалей library.json на GitHub!")
