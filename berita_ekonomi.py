"""
Ringkasan Berita Makro & Mikro Ekonomi Indonesia -> Telegram
Jalan tiap hari via GitHub Actions (08:00 WIB).
Sumber RSS terpercaya: CNBC Indonesia, Katadata, Antara.
Tanpa API key / tanpa biaya.
"""
import os
import re
import html
import feedparser
import requests
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

WIB = timezone(timedelta(hours=7))

FEEDS = {
    "CNBC": "https://www.cnbcindonesia.com/rss",
    "Katadata": "https://katadata.co.id/rss",
    "Antara Bisnis": "https://www.antaranews.com/rss/ekonomi",
}

# Kata kunci klasifikasi
MAKRO_KEYS = [
    "ihsg", "rupiah", "dolar", "inflasi", "bi rate", "suku bunga", "apbn", "pdb",
    "ekonomi", "imf", "msci", "bei", "saham", "obligasi", "sbn", "emiten",
    "minyak", "batu bara", "bahlil", "pajak", "impor", "ekspor", "investasi",
    "hilirisasi", "bbm", "oecd", "untdad", "unctad", "pertumbuhan",
]
MIKRO_KEYS = [
    "umkm", "mekar", "pnm", "halal", "koperasi", "warung", "pasar", "bansos",
    "lpg", "kdkmp", "indomaret", "promo", "diskon", "krl", "bumn", "phk",
    "kerja", "upah", "gaji", "asn",
]

def clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def fetch(max_per_feed: int = 15):
    items = []
    for source, url in FEEDS.items():
        try:
            d = feedparser.parse(url)
            for e in d.entries[:max_per_feed]:
                title = clean(getattr(e, "title", ""))
                desc = clean(getattr(e, "summary", "") or getattr(e, "description", ""))
                link = getattr(e, "link", "")
                pub = getattr(e, "published", "")
                if not title or not link:
                    continue
                low = (title + " " + desc).lower()
                cat = "Lainnya"
                if any(k in low for k in MAKRO_KEYS):
                    cat = "Makro"
                if any(k in low for k in MIKRO_KEYS):
                    # UMKM / konsumen diprioritaskan sebagai Mikro walau mengandung kata makro
                    cat = "Mikro"
                items.append({"source": source, "title": title, "desc": desc, "link": link, "pub": pub, "cat": cat})
        except Exception as ex:
            print(f"Gagal fetch {source}: {ex}")
    return items

def pick(items, cat, n=7):
    out, seen = [], set()
    for it in items:
        if it["cat"] != cat:
            continue
        key = it["title"].lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
        if len(out) >= n:
            break
    return out

def build_message(items) -> str:
    now = datetime.now(WIB).strftime("%A, %d %B %Y")
    makro = pick(items, "Makro", 7)
    mikro = pick(items, "Mikro", 5)
    # fallback: jika mikro kosong, ambil dari Lainnya
    if len(mikro) < 3:
        extra = [x for x in items if x["cat"] == "Lainnya"][: 5 - len(mikro)]
        mikro += extra
    if not makro:
        makro = items[:7]

    lines = [f"<b>Ringkasan Ekonomi Indonesia</b>", f"{now} — 08:00 WIB", ""]
    lines.append("<b>1. MAKRO (Nasional & Pasar)</b>")
    for i, it in enumerate(makro, 1):
        desc = it["desc"][:140] + ("..." if len(it["desc"]) > 140 else "")
        lines.append(f'{i}. <a href="{it["link"]}">{html.escape(it["title"])}</a>')
        lines.append(f'   [{it["source"]}] {html.escape(desc)}')
    lines.append("")
    lines.append("<b>2. MIKRO (UMKM, Konsumen, Energi Harian)</b>")
    for i, it in enumerate(mikro, 1):
        desc = it["desc"][:140] + ("..." if len(it["desc"]) > 140 else "")
        lines.append(f'{i}. <a href="{it["link"]}">{html.escape(it["title"])}</a>')
        lines.append(f'   [{it["source"]}] {html.escape(desc)}')
    lines.append("")
    lines.append("Sumber: CNBC Indonesia, Katadata, Antara. Klik judul untuk baca penuh.")
    msg = "\n".join(lines)
    # Telegram batas 4096 karakter
    if len(msg) > 3900:
        msg = msg[:3900] + "\n... (dipotong)"
    return msg

def send(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID belum di-set. Pesan:")
        print(msg[:2000])
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=30)
    print(r.status_code, r.text[:500])
    return r.ok

if __name__ == "__main__":
    data = fetch()
    print(f"Terkumpul {len(data)} berita")
    msg = build_message(data)
    ok = send(msg)
    if not ok:
        raise SystemExit(1)
