#!/usr/bin/env python3
"""Parse the `irk_bitig` wiki-source file into structured JSON.

Usage:
  python parse_irk_bitig.py --input irk_bitig --output irk_bitig.json --pretty

Outputs a JSON array of omens with fields: `number`, `pattern`, `circles`,
`divination`, `transliteration`, `transcription` and a `header` object when present.

This script uses only Python standard library modules.
"""
# AI-produced code
# Kept to harvest any interesting parts.

import argparse
import json
import re
from pathlib import Path
import sys


def parse_header(text):
    m = re.search(r"\{\{header(.*?)\}\}", text, re.DOTALL)
    if not m:
        return {}
    body = m.group(1)
    header = {}
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = line[1:].split("=", 1)
        if len(parts) != 2:
            continue
        key = parts[0].strip()
        val = parts[1].strip()
        # strip surrounding quotes
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        header[key] = val
    return header


def _clean(s):
    if s is None:
        return ""
    # remove leading/trailing whitespace and canonicalize inner whitespace
    s = s.strip()
    s = s.replace('\r', '')
    # remove html <br/> markers
    s = re.sub(r"<br\s*/?>", '\n', s, flags=re.IGNORECASE)
    # collapse multiple whitespace to single space, but keep newlines
    s = '\n'.join(' '.join(line.split()) for line in s.splitlines())
    return s


def parse_omens(text):
    # find positions of all <!--Omen N: ...--> markers
    omen_re = re.compile(r"<!--\s*Omen\s*(\d+):\s*(.*?)-->", re.DOTALL)
    omen_positions = [m for m in omen_re.finditer(text)]
    omens = []
    for idx, m in enumerate(omen_positions):
        num = int(m.group(1))
        pattern = _clean(m.group(2))
        start = m.end()
        end = omen_positions[idx + 1].start() if idx + 1 < len(omen_positions) else len(text)
        region = text[start:end]
        # circles (first RTL after the omen comment)
        circles = ''
        mcir = re.search(r"\{\{RTL\|(.*?)\}\}", region, re.DOTALL)
        if mcir:
            circles = _clean(mcir.group(1))
            # move region cursor after circles for subsequent searches
            region_after_circles = region[mcir.end():]
        else:
            region_after_circles = region
        # divination (RTL after <!--Divination ..-->)
        # there is often a "<!--Divination N-->" marker; find it and then the next RTL
        divination = ''
        mdiv_marker = re.search(r"<!--\s*Divination\s*\d+\s*-->", region_after_circles)
        search_region_for_div = region_after_circles
        if mdiv_marker:
            search_region_for_div = region_after_circles[mdiv_marker.end():]
        mdiv = re.search(r"\{\{RTL\|(.*?)\}\}", search_region_for_div, re.DOTALL)
        if mdiv:
            divination = _clean(mdiv.group(1))
            post_div_region = search_region_for_div[mdiv.end():]
        else:
            post_div_region = search_region_for_div
        # transliteration and transcription comments in the following region
        transliteration = ''
        transcription = ''
        mtr = re.search(r"<!--\s*Transliteration\s*:\s*(.*?)-->", post_div_region, re.DOTALL)
        if mtr:
            transliteration = _clean(mtr.group(1))
        mtr2 = re.search(r"<!--\s*Transcription\s*:\s*(.*?)-->", post_div_region, re.DOTALL)
        if mtr2:
            transcription = _clean(mtr2.group(1))
        omens.append({
            'number': num,
            'pattern': pattern,
            'circles': circles,
            'divination': divination,
            'transliteration': transliteration,
            'transcription': transcription,
        })
    return omens


def main(argv=None):
    p = argparse.ArgumentParser(description='Parse an irk_bitig wiki file into JSON')
    p.add_argument('--input', '-i', default='irk_bitig', help='input filepath (default: irk_bitig)')
    p.add_argument('--output', '-o', help='output filepath (JSON). if omitted prints to stdout')
    p.add_argument('--pretty', action='store_true', help='pretty-print JSON')
    args = p.parse_args(argv)

    path = Path(args.input)
    if not path.exists():
        print(f'Input file not found: {path}', file=sys.stderr)
        return 2
    text = path.read_text(encoding='utf-8')

    header = parse_header(text)
    omens = parse_omens(text)

    out = {
        'source': str(path),
        'header': header,
        'omens': omens,
    }

    if args.output:
        out_path = Path(args.output)
        if args.pretty:
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        else:
            out_path.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        print(f'Wrote {out_path}')
    else:
        if args.pretty:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
