# utils/address_parser.py
import re

def parse_hungarian_address(address: str) -> str:
    """
    Magyar cím parser - rövidítések és irányítószámok felismerése
    """
    if not address or not address.strip():
        return ""
    
    addr = address.strip()
    
    # Irányítószám felismerés és normalizálás
    # "1051 Budapest" -> "1051 Budapest"
    # "Budapest 1051" -> "1051 Budapest"
    postal_pattern = r'(\d{4})\s*([A-ZÁÉÍÓÖŐÚÜŰ][a-záéíóöőúüű\s]+)'
    match = re.search(postal_pattern, addr)
    if match:
        postal_code, city = match.groups()
        addr = f"{postal_code} {city.strip()}"
    
    # Magyar rövidítések felismerése és kibővítése
    abbreviations = {
        r'\bsgt\b': 'sugárút',
        r'\bkrt\b': 'körút', 
        r'\but\b': 'utca',
        r'\bút\b': 'utca',
        r'\btér\b': 'tér',
        r'\bpl\b': 'pályaudvar',
        r'\báll\b': 'állomás',
        r'\bker\b': 'kerület',
        r'\bker\.\b': 'kerület',
        r'\bV\.\s*ker\b': 'V. kerület',
        r'\bI\.\s*ker\b': 'I. kerület',
        r'\bII\.\s*ker\b': 'II. kerület',
        r'\bIII\.\s*ker\b': 'III. kerület',
        r'\bIV\.\s*ker\b': 'IV. kerület',
        r'\bVI\.\s*ker\b': 'VI. kerület',
        r'\bVII\.\s*ker\b': 'VII. kerület',
        r'\bVIII\.\s*ker\b': 'VIII. kerület',
        r'\bIX\.\s*ker\b': 'IX. kerület',
        r'\bX\.\s*ker\b': 'X. kerület',
        r'\bXI\.\s*ker\b': 'XI. kerület',
        r'\bXII\.\s*ker\b': 'XII. kerület',
        r'\bXIII\.\s*ker\b': 'XIII. kerület',
        r'\bXIV\.\s*ker\b': 'XIV. kerület',
        r'\bXV\.\s*ker\b': 'XV. kerület',
        r'\bXVI\.\s*ker\b': 'XVI. kerület',
        r'\bXVII\.\s*ker\b': 'XVII. kerület',
        r'\bXVIII\.\s*ker\b': 'XVIII. kerület',
        r'\bXIX\.\s*ker\b': 'XIX. kerület',
        r'\bXX\.\s*ker\b': 'XX. kerület',
        r'\bXXI\.\s*ker\b': 'XXI. kerület',
        r'\bXXII\.\s*ker\b': 'XXII. kerület',
        r'\bXXIII\.\s*ker\b': 'XXIII. kerület'
    }
    
    for pattern, replacement in abbreviations.items():
        addr = re.sub(pattern, replacement, addr, flags=re.IGNORECASE)
    
    # Dupla szóközök eltávolítása
    addr = re.sub(r'\s+', ' ', addr).strip()
    
    return addr
