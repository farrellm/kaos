#!/usr/bin/env python3
"""
KAOS (Netflix 2024) - Transcript Downloader & Formatter
Downloads subtitle files and generates plain text and Markdown transcripts
for all 8 episodes of Season 1.
"""

import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "transcripts")
SRT_DIR = os.path.join(TRANSCRIPTS_DIR, "srt")
TXT_DIR = os.path.join(TRANSCRIPTS_DIR, "txt")
MD_DIR = os.path.join(TRANSCRIPTS_DIR, "md")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
BASE_URL = "https://www.subtitlecat.com"

def srt_to_clean_txt(srt_content: str) -> str:
    """Convert raw SRT subtitles into readable plain text."""
    srt_content = srt_content.lstrip("\ufeff")
    blocks = re.split(r"\n\s*\n", srt_content.strip())
    lines_out = []
    prev = ""
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            text = " ".join(lines[2:]).strip()
        elif len(lines) == 2 and "-->" in lines[0]:
            text = lines[1].strip()
        else:
            continue
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text and text != prev:
            lines_out.append(text)
            prev = text
    return "\n".join(lines_out)

def srt_to_markdown(ep_num: int, srt_content: str) -> str:
    """Convert raw SRT subtitles into structured Markdown."""
    srt_content = srt_content.lstrip("\ufeff")
    blocks = re.split(r"\n\s*\n", srt_content.strip())
    
    md_lines = [
        f"# KAOS - Season 1, Episode {ep_num}",
        "",
        "**Series:** KAOS (Netflix 2024)",
        "**Season:** 1",
        f"**Episode:** {ep_num}",
        "",
        "---",
        ""
    ]
    
    prev_text = ""
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            timestamp = lines[1].split(" --> ")[0]
            text = " ".join(lines[2:]).strip()
        elif len(lines) == 2 and "-->" in lines[0]:
            timestamp = lines[0].split(" --> ")[0]
            text = lines[1].strip()
        else:
            continue
            
        text = re.sub(r"<[^>]+>", "", text).strip()
        if not text or text == prev_text:
            continue
        prev_text = text
        
        if text.startswith("[") and text.endswith("]"):
            md_lines.append(f"*{text}*\n")
        elif text.startswith("-"):
            subparts = [p.strip() for p in text.split("-") if p.strip()]
            for part in subparts:
                md_lines.append(f"- {part}")
            md_lines.append("")
        else:
            md_lines.append(f"{text}\n")
            
    return "\n".join(md_lines)

def main():
    os.makedirs(SRT_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(MD_DIR, exist_ok=True)

    print("Downloading KAOS Season 1 Transcripts...")
    full_season_txt = []

    for ep in range(1, 9):
        ep_str = f"{ep:02d}"
        page_url = f"https://www.subtitlecat.com/subs/838/KAOS_S01E{ep_str}_Episode%20{ep}.en.closedcaptions.html"
        resp = requests.get(page_url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"Error fetching page for Episode {ep}: HTTP {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        srt_link = None
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href.endswith("-en.srt"):
                srt_link = href
                break
                
        if not srt_link:
            print(f"Failed to find SRT URL for Episode {ep}")
            continue
            
        srt_url = urllib.parse.urljoin(BASE_URL, srt_link)
        srt_resp = requests.get(srt_url, headers=HEADERS)
        srt_content = srt_resp.text
        
        # Save raw SRT
        srt_file = os.path.join(SRT_DIR, f"KAOS_S01E{ep_str}.srt")
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write(srt_content)
            
        # Save clean TXT
        clean_text = srt_to_clean_txt(srt_content)
        txt_file = os.path.join(TXT_DIR, f"KAOS_S01E{ep_str}.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(clean_text)
            
        # Save structured Markdown
        md_content = srt_to_markdown(ep, srt_content)
        md_file = os.path.join(MD_DIR, f"KAOS_S01E{ep_str}.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        full_season_txt.append(
            f"==================================================\n"
            f"KAOS - SEASON 1, EPISODE {ep}\n"
            f"==================================================\n\n"
            f"{clean_text}"
        )
        print(f"✓ Episode {ep}: Saved SRT ({len(srt_content)} bytes), TXT ({len(clean_text)} chars), MD")

    full_season_path = os.path.join(TRANSCRIPTS_DIR, "KAOS_Season_1_Complete.txt")
    with open(full_season_path, "w", encoding="utf-8") as f:
        f.write("\n\n\n".join(full_season_txt))

    print(f"\nAll transcripts downloaded successfully to: {TRANSCRIPTS_DIR}")

if __name__ == "__main__":
    main()
