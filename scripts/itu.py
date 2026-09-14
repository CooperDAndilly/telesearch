# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pypdf>=3.0.0",
# ]
# ///

"""
ITU-T E.164 Country Code Scraper & Converter

Downloads and parses the official ITU Operational Bulletin annex:
"List of Recommendation ITU-T E.164 assigned country codes" (OB 1114)
and pairs country names with their official ISO 3166-1 alpha-2 codes
using the official United Nations Statistics Division (UN M49 / ISO 3166-1) standard.

Output format:
<Country>,<iso2>,+<calling_code>
e.g.
Australia,au,+61
"""

import argparse
import csv
import html
import json
import os
import re
import sys
import urllib.request
from typing import Dict, List, Optional, Tuple

# Official ITU E.164 assigned country codes annex PDF (Position on 15 Dec 2016, OB 1114)
DEFAULT_ITU_PDF_URL = "https://www.itu.int/dms_pub/itu-t/opb/sp/T-SP-E.164D-2016-PDF-E.pdf"
LOCAL_PDF_FILENAME = "T-SP-E.164D-2016-PDF-E.pdf"

# Official United Nations Statistics Division (UN M49) standard country data
UN_M49_URL = "https://unstats.un.org/unsd/methodology/m49/overview/"

# Official UN M49 Country / Area Code -> ISO 3166-1 alpha-2 standard dataset
# Source: United Nations Statistics Division (UNSD) M49 Standard
OFFICIAL_UN_M49_ISO_DATA: Dict[str, str] = {
    "Algeria": "dz",
    "Egypt": "eg",
    "Libya": "ly",
    "Morocco": "ma",
    "Sudan": "sd",
    "Tunisia": "tn",
    "Western Sahara": "eh",
    "British Indian Ocean Territory": "io",
    "Burundi": "bi",
    "Comoros": "km",
    "Djibouti": "dj",
    "Eritrea": "er",
    "Ethiopia": "et",
    "French Southern Territories": "tf",
    "Kenya": "ke",
    "Madagascar": "mg",
    "Malawi": "mw",
    "Mauritius": "mu",
    "Mayotte": "yt",
    "Mozambique": "mz",
    "Réunion": "re",
    "Rwanda": "rw",
    "Seychelles": "sc",
    "Somalia": "so",
    "South Sudan": "ss",
    "Uganda": "ug",
    "United Republic of Tanzania": "tz",
    "Zambia": "zm",
    "Zimbabwe": "zw",
    "Angola": "ao",
    "Cameroon": "cm",
    "Central African Republic": "cf",
    "Chad": "td",
    "Congo": "cg",
    "Democratic Republic of the Congo": "cd",
    "Equatorial Guinea": "gq",
    "Gabon": "ga",
    "Sao Tome and Principe": "st",
    "Botswana": "bw",
    "Eswatini": "sz",
    "Lesotho": "ls",
    "Namibia": "na",
    "South Africa": "za",
    "Benin": "bj",
    "Burkina Faso": "bf",
    "Cabo Verde": "cv",
    "Côte d'Ivoire": "ci",
    "Gambia": "gm",
    "Ghana": "gh",
    "Guinea": "gn",
    "Guinea-Bissau": "gw",
    "Liberia": "lr",
    "Mali": "ml",
    "Mauritania": "mr",
    "Niger": "ne",
    "Nigeria": "ng",
    "Saint Helena": "sh",
    "Senegal": "sn",
    "Sierra Leone": "sl",
    "Togo": "tg",
    "Anguilla": "ai",
    "Antigua and Barbuda": "ag",
    "Aruba": "aw",
    "Bahamas": "bs",
    "Barbados": "bb",
    "Bonaire, Sint Eustatius and Saba": "bq",
    "British Virgin Islands": "vg",
    "Cayman Islands": "ky",
    "Cuba": "cu",
    "Curaçao": "cw",
    "Dominica": "dm",
    "Dominican Republic": "do",
    "Grenada": "gd",
    "Guadeloupe": "gp",
    "Haiti": "ht",
    "Jamaica": "jm",
    "Martinique": "mq",
    "Montserrat": "ms",
    "Puerto Rico": "pr",
    "Saint Barthélemy": "bl",
    "Saint Kitts and Nevis": "kn",
    "Saint Lucia": "lc",
    "Saint Martin (French part)": "mf",
    "Saint Vincent and the Grenadines": "vc",
    "Sint Maarten (Dutch part)": "sx",
    "Trinidad and Tobago": "tt",
    "Turks and Caicos Islands": "tc",
    "United States Virgin Islands": "vi",
    "Belize": "bz",
    "Costa Rica": "cr",
    "El Salvador": "sv",
    "Guatemala": "gt",
    "Honduras": "hn",
    "Mexico": "mx",
    "Nicaragua": "ni",
    "Panama": "pa",
    "Argentina": "ar",
    "Bolivia (Plurinational State of)": "bo",
    "Bouvet Island": "bv",
    "Brazil": "br",
    "Chile": "cl",
    "Colombia": "co",
    "Ecuador": "ec",
    "Falkland Islands (Malvinas)": "fk",
    "French Guiana": "gf",
    "Guyana": "gy",
    "Paraguay": "py",
    "Peru": "pe",
    "South Georgia and the South Sandwich Islands": "gs",
    "Suriname": "sr",
    "Uruguay": "uy",
    "Venezuela (Bolivarian Republic of)": "ve",
    "Bermuda": "bm",
    "Canada": "ca",
    "Greenland": "gl",
    "Saint Pierre and Miquelon": "pm",
    "United States of America": "us",
    "Antarctica": "aq",
    "Kazakhstan": "kz",
    "Kyrgyzstan": "kg",
    "Tajikistan": "tj",
    "Turkmenistan": "tm",
    "Uzbekistan": "uz",
    "China": "cn",
    "China, Hong Kong Special Administrative Region": "hk",
    "China, Macao Special Administrative Region": "mo",
    "Dem. People's Rep. of Korea": "kp",
    "Japan": "jp",
    "Mongolia": "mn",
    "Republic of Korea": "kr",
    "Afghanistan": "af",
    "Bangladesh": "bd",
    "Bhutan": "bt",
    "India": "in",
    "Iran (Islamic Republic of)": "ir",
    "Maldives": "mv",
    "Nepal": "np",
    "Pakistan": "pk",
    "Sri Lanka": "lk",
    "Brunei Darussalam": "bn",
    "Cambodia": "kh",
    "Indonesia": "id",
    "Lao People's Dem. Republic": "la",
    "Malaysia": "my",
    "Myanmar": "mm",
    "Philippines": "ph",
    "Singapore": "sg",
    "Thailand": "th",
    "Timor-Leste": "tl",
    "Viet Nam": "vn",
    "Armenia": "am",
    "Azerbaijan": "az",
    "Bahrain": "bh",
    "Cyprus": "cy",
    "Georgia": "ge",
    "Iraq": "iq",
    "Israel": "il",
    "Jordan": "jo",
    "Kuwait": "kw",
    "Lebanon": "lb",
    "Oman": "om",
    "Qatar": "qa",
    "Saudi Arabia": "sa",
    "State of Palestine": "ps",
    "Syrian Arab Republic": "sy",
    "Türkiye": "tr",
    "United Arab Emirates": "ae",
    "Yemen": "ye",
    "Belarus": "by",
    "Bulgaria": "bg",
    "Czechia": "cz",
    "Hungary": "hu",
    "Poland": "pl",
    "Republic of Moldova": "md",
    "Romania": "ro",
    "Russian Federation": "ru",
    "Slovakia": "sk",
    "Ukraine": "ua",
    "Åland Islands": "ax",
    "Channel Islands": "gg",
    "Denmark": "dk",
    "Estonia": "ee",
    "Faroe Islands": "fo",
    "Finland": "fi",
    "Guernsey": "gg",
    "Iceland": "is",
    "Ireland": "ie",
    "Isle of Man": "im",
    "Jersey": "je",
    "Latvia": "lv",
    "Lithuania": "lt",
    "Norway": "no",
    "Svalbard and Jan Mayen Islands": "sj",
    "Sweden": "se",
    "United Kingdom of Great Britain and Northern Ireland": "gb",
    "Albania": "al",
    "Andorra": "ad",
    "Bosnia and Herzegovina": "ba",
    "Croatia": "hr",
    "Gibraltar": "gi",
    "Greece": "gr",
    "Holy See": "va",
    "Italy": "it",
    "Malta": "mt",
    "Montenegro": "me",
    "North Macedonia": "mk",
    "Portugal": "pt",
    "San Marino": "sm",
    "Serbia": "rs",
    "Slovenia": "si",
    "Spain": "es",
    "Austria": "at",
    "Belgium": "be",
    "France": "fr",
    "Germany": "de",
    "Liechtenstein": "li",
    "Luxembourg": "lu",
    "Monaco": "mc",
    "Netherlands (Kingdom of the)": "nl",
    "Switzerland": "ch",
    "Australia": "au",
    "Christmas Island": "cx",
    "Cocos (Keeling) Islands": "cc",
    "Heard Island and McDonald Islands": "hm",
    "New Zealand": "nz",
    "Norfolk Island": "nf",
    "Fiji": "fj",
    "New Caledonia": "nc",
    "Papua New Guinea": "pg",
    "Solomon Islands": "sb",
    "Vanuatu": "vu",
    "Guam": "gu",
    "Kiribati": "ki",
    "Marshall Islands": "mh",
    "Micronesia (Federated States of)": "fm",
    "Nauru": "nr",
    "Northern Mariana Islands": "mp",
    "Palau": "pw",
    "United States Minor Outlying Islands": "um",
    "American Samoa": "as",
    "Cook Islands": "ck",
    "French Polynesia": "pf",
    "Niue": "nu",
    "Pitcairn": "pn",
    "Samoa": "ws",
    "Tokelau": "tk",
    "Tonga": "to",
    "Tuvalu": "tv",
    "Wallis and Futuna Islands": "wf",
}

# Formal ITU diplomatic names mapped to UN/ISO short names and codes
ITU_NAME_ALIASES: Dict[str, Tuple[str, str]] = {
    'Argentine Republic': ('Argentina', 'ar'),
    'Australian External Territories': ('Norfolk Island', 'nf'),
    'Bolivia (Plurinational State of)': ('Bolivia', 'bo'),
    'Bonaire, Sint Eustatius and Saba': ('Bonaire, Sint Eustatius and Saba', 'bq'),
    'British Virgin Islands': ('British Virgin Islands', 'vg'),
    'Brunei Darussalam': ('Brunei', 'bn'),
    'Côte d\'Ivoire (Republic of)': ('Côte d\'Ivoire', 'ci'),
    'Cte d\'Ivoire (Republic of)': ('Côte d\'Ivoire', 'ci'),
    'Curaçao': ('Curaçao', 'cw'),
    'Curaao': ('Curaçao', 'cw'),
    'Czech Republic': ('Czechia', 'cz'),
    'Democratic People\'s Republic of Korea': ('North Korea', 'kp'),
    'Democratic Republic of the Congo': ('Democratic Republic of the Congo', 'cd'),
    'Diego Garcia': ('Diego Garcia', 'io'),
    'French Departments and Territories in the Indian Ocean': ('Réunion', 're'),
    'French Polynesia (Territoire français d\'outre-mer)': ('French Polynesia', 'pf'),
    'French Polynesia (Territoire franais d\'outre-mer)': ('French Polynesia', 'pf'),
    'Gabonese Republic': ('Gabon', 'ga'),
    'Holy See (Vatican City State)': ('Holy See', 'va'),
    'Hong Kong, China': ('Hong Kong', 'hk'),
    'Iran (Islamic Republic of)': ('Iran', 'ir'),
    'Kazakhstan (Republic of)': ('Kazakhstan', 'kz'),
    'Korea (Republic of)': ('South Korea', 'kr'),
    'Kosovo*': ('Kosovo', 'xk'),
    'Kyrgyz Republic': ('Kyrgyzstan', 'kg'),
    'Lao People\'s Democratic Republic': ('Laos', 'la'),
    'Macao, China': ('Macao', 'mo'),
    'Micronesia (Federated States of)': ('Micronesia', 'fm'),
    'Moldova (Republic of)': ('Moldova', 'md'),
    'Nauru (Republic of)': ('Nauru', 'nr'),
    'New Caledonia (Territoire français d\'outre-mer)': ('New Caledonia', 'nc'),
    'New Caledonia (Territoire franais d\'outre-mer)': ('New Caledonia', 'nc'),
    'Russian Federation': ('Russia', 'ru'),
    'Saint Helena, Ascension and Tristan da Cunha': ('Saint Helena', 'sh'),
    'Saint Pierre and Miquelon (Collectivité territoriale de la République française)': ('Saint Pierre and Miquelon', 'pm'),
    'Saint Pierre and Miquelon (Collectivit territoriale de la Rpublique franaise)': ('Saint Pierre and Miquelon', 'pm'),
    'Sint Maarten (Dutch part)': ('Sint Maarten', 'sx'),
    'Slovak Republic': ('Slovakia', 'sk'),
    'Swaziland (Kingdom of)': ('Eswatini', 'sz'),
    'Syrian Arab Republic': ('Syria', 'sy'),
    'Taiwan, China': ('Taiwan', 'tw'),
    'Tanzania (United Republic of)': ('Tanzania', 'tz'),
    'The Former Yugoslav Republic of Macedonia': ('North Macedonia', 'mk'),
    'Togolese Republic': ('Togo', 'tg'),
    'Turkey': ('Turkey', 'tr'),
    'United Kingdom of Great Britain and Northern Ireland': ('United Kingdom', 'gb'),
    'United States of America': ('United States', 'us'),
    'United States Virgin Islands': ('United States Virgin Islands', 'vi'),
    'Vatican City State': ('Holy See', 'va'),
    'Venezuela (Bolivarian Republic of)': ('Venezuela', 've'),
    'Viet Nam (Socialist Republic of)': ('Vietnam', 'vn'),
    'Wallis and Futuna (Territoire français d\'outre-mer)': ('Wallis and Futuna', 'wf'),
    'Wallis and Futuna (Territoire franais d\'outre-mer)': ('Wallis and Futuna', 'wf'),
}


def download_file(url: str, target_path: str) -> None:
    """Download a file via HTTP GET if missing."""
    print(f"Downloading from {url}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        content = response.read()
        with open(target_path, 'wb') as f:
            f.write(content)
    print(f"Saved {len(content)} bytes to {target_path}")


def fetch_live_un_m49() -> Dict[str, str]:
    """Fetch live country data from United Nations Statistics Division (UNSD)."""
    print(f"Fetching official UN M49 country table from {UN_M49_URL}...")
    req = urllib.request.Request(UN_M49_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        page_html = resp.read().decode('utf-8', errors='ignore')

    tables = re.findall(r'<table[^>]*>(.*?)</table>', page_html, re.S)
    if not tables:
        print("Warning: Could not parse UN M49 tables from web, using embedded UN dataset.")
        return OFFICIAL_UN_M49_ISO_DATA

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[0], re.S)
    live_un = {}
    for r in rows[1:]:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
        cells = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in cells]
        if len(cells) >= 11:
            c_name = cells[8]
            iso2 = cells[10].lower()
            if iso2:
                live_un[c_name] = iso2
    print(f"Fetched {len(live_un)} countries from UN Statistics Division.")
    return live_un


def extract_lines_from_pdf(pdf_path: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Extract entries from the alphabetical table section of the ITU PDF.
    Pages 10 to 16 contain the alphabetical list of assigned country codes.
    """
    try:
        import pypdf
    except ImportError:
        print("Error: 'pypdf' package is required. Install via `pip install pypdf` or run with `uv run`.")
        sys.exit(1)

    reader = pypdf.PdfReader(pdf_path)
    raw_lines = []

    # In OB 1114, pages 10 to 16 (0-indexed: 9 to 15) contain the alphabetical table
    for page_idx in range(9, 16):
        text = reader.pages[page_idx].extract_text()
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if 'Annex to ITU' in line or 'List of Rec.' in line or 'Country code Country' in line or 'assigned country codes' in line:
                continue
            raw_lines.append(line)

    # Merge wrapped lines
    merged_lines = []
    for line in raw_lines:
        if re.match(r'^\d+\s+', line):
            merged_lines.append(line)
        else:
            if merged_lines:
                merged_lines[-1] += ' ' + line
            else:
                merged_lines.append(line)

    pattern = re.compile(r'^(\d+)\s+(.+?)(?:\s+([a-z](?:,\s*[a-z])*))?$')
    entries = []
    for line in merged_lines:
        m = pattern.match(line)
        if m:
            code, name, note = m.groups()
            entries.append((code, name.strip(), note))

    return entries


def map_entries_to_un_iso(
    entries: List[Tuple[str, str, Optional[str]]],
    un_dataset: Dict[str, str]
) -> List[Tuple[str, str, str]]:
    """Map ITU parsed entries to standard country names, ISO 3166-1 alpha-2, and +CallingCode."""
    # Normalize UN dataset keys for case-insensitive matching
    un_lookup = {k.lower(): (k, v) for k, v in un_dataset.items()}

    rows = []
    for code, orig_name, note in entries:
        name = orig_name.strip()
        name_low = name.lower()

        # Skip spare, reserved, and non-geographic shared global services
        if 'spare code' in name_low or (name_low == 'reserved' and code != '970'):
            continue
        if 'shared code' in name_low or 'service' in name_low or 'reserved' in name_low:
            continue
        if 'inmarsat' in name_low or 'telecommunications for disaster' in name_low:
            continue

        # Palestine (+970) is noted under footnote 'l' in the ITU table
        if code == '970':
            rows.append(('Palestine', 'ps', '+970'))
            continue

        iso2 = None
        display_name = name

        # 1. Check ITU-to-UN / ISO alias map
        matched = False
        for k, (v_name, v_iso) in ITU_NAME_ALIASES.items():
            if k.lower() == name_low or k.lower() in name_low:
                display_name, iso2 = v_name, v_iso
                matched = True
                break

        # 2. Check directly in UN M49 dataset
        if not matched:
            clean = re.sub(r'\s*\([^)]*\)', '', name).strip()
            clean_low = clean.lower()
            if clean_low in un_lookup:
                display_name = clean
                iso2 = un_lookup[clean_low][1]
            elif name_low in un_lookup:
                display_name = clean
                iso2 = un_lookup[name_low][1]

        if iso2:
            rows.append((display_name, iso2, f'+{code}'))

    # Sort alphabetically by country name
    rows.sort(key=lambda r: r[0].lower())
    return rows


def write_csv(rows: List[Tuple[str, str, str]], output_path: str, include_header: bool = False) -> None:
    """Write rows to a CSV file."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if include_header:
            writer.writerow(['Country', 'ISO2', 'CallingCode'])
        for row in rows:
            writer.writerow(row)
    print(f"Successfully written {len(rows)} entries to '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape ITU-T E.164 assigned country codes from official PDF and map using UN M49 ISO standard."
    )
    parser.add_argument(
        '--pdf',
        default=LOCAL_PDF_FILENAME,
        help=f"Path to ITU PDF file (default: '{LOCAL_PDF_FILENAME}'). Downloaded if missing."
    )
    parser.add_argument(
        '--url',
        default=DEFAULT_ITU_PDF_URL,
        help="URL to download the ITU PDF from if not found locally."
    )
    parser.add_argument(
        '--output', '-o',
        default='itu_country_codes.csv',
        help="Output CSV file path (default: 'itu_country_codes.csv')."
    )
    parser.add_argument(
        '--header',
        action='store_true',
        help="Include a CSV header row ('Country,ISO2,CallingCode'). Default is False."
    )
    parser.add_argument(
        '--refresh-un',
        action='store_true',
        help="Fetch fresh UN M49 country data live from unstats.un.org instead of embedded dataset."
    )

    args = parser.parse_args()

    # Load UN M49 country data
    un_dataset = fetch_live_un_m49() if args.refresh_un else OFFICIAL_UN_M49_ISO_DATA

    # Ensure PDF exists
    if not os.path.exists(args.pdf):
        download_file(args.url, args.pdf)

    # Extract lines from PDF
    print(f"Parsing ITU PDF: {args.pdf}...")
    entries = extract_lines_from_pdf(args.pdf)
    print(f"Extracted {len(entries)} entries from ITU table.")

    # Map with official UN M49 / ISO standard
    rows = map_entries_to_un_iso(entries, un_dataset)
    print(f"Mapped {len(rows)} countries using official UN M49 / ISO 3166-1 standard.")

    # Write output
    write_csv(rows, args.output, include_header=args.header)

    # Preview
    print("\nSample Output:")
    for r in rows[:5]:
        print(f"{r[0]},{r[1]},{r[2]}")
    for r in rows:
        if r[0] == 'Australia':
            print(f"...\n{r[0]},{r[1]},{r[2]}\n...")
            break


if __name__ == '__main__':
    main()
