# utils/geocoding.py
import requests
import math
import time
import logging
from typing import List, Optional, Tuple
from utils.address_parser import parse_hungarian_address

logger = logging.getLogger(__name__)

def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Cím geokódolása Nominatim API-val
    """
    try:
        time.sleep(0.5)  # Udvarias várakozás
        
        parsed_addr = parse_hungarian_address(address)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': parsed_addr,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'hu',
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'OPDBot/1.0 (Delivery Navigation)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return (lat, lon)
    except Exception as e:
        logger.error(f"Geocoding error for '{address}': {e}")
    return None

def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Haversine formula - légvonalbeli távolság két koordináta között (km-ben)
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371.0  # Föld sugara km-ben
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def optimize_route(addresses: List[str]) -> List[str]:
    """
    Egyszerű útvonal optimalizálás - legközelebbi szomszéd algoritmus
    """
    if len(addresses) <= 1:
        return addresses
    
    # Maximum 6 cím (teljesítmény miatt)
    if len(addresses) > 6:
        logger.warning(f"Too many addresses ({len(addresses)}), limiting to 6")
        addresses = addresses[:6]
    
    # Geokódolás
    coords = []
    valid_addresses = []
    
    for addr in addresses:
        coord = geocode_address(addr)
        if coord:
            coords.append(coord)
            valid_addresses.append(addr)
        else:
            logger.warning(f"Could not geocode address: {addr}")
    
    if len(valid_addresses) <= 1:
        return valid_addresses
    
    # Legközelebbi szomszéd algoritmus
    optimized = [valid_addresses[0]]  # Első cím
    remaining = list(range(1, len(valid_addresses)))
    current_coord = coords[0]
    
    while remaining:
        min_distance = float('inf')
        next_idx = remaining[0]
        
        for idx in remaining:
            distance = haversine_distance(current_coord, coords[idx])
            if distance < min_distance:
                min_distance = distance
                next_idx = idx
        
        optimized.append(valid_addresses[next_idx])
        current_coord = coords[next_idx]
        remaining.remove(next_idx)
    
    logger.info(f"Route optimized: {len(valid_addresses)} addresses")
    return optimized
