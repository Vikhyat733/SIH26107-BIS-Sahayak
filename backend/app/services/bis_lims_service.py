import httpx
from bs4 import BeautifulSoup
import re
import datetime
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(standard: str) -> Path:
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', standard.lower())
    return CACHE_DIR / f"lims_{safe_name}.json"

def _is_cache_valid(cache_path: Path, max_age_hours=24) -> bool:
    if not cache_path.exists():
        return False
    mtime = datetime.datetime.fromtimestamp(cache_path.stat().st_mtime)
    age = datetime.datetime.now() - mtime
    return age.total_seconds() < (max_age_hours * 3600)

def search_labs_by_standard(is_number_val: str, standard_full: str) -> List[Dict[str, Any]]:
    """
    Search BIS LIMS for laboratories supporting the given IS number.
    Uses caching to avoid live scraping issues if run frequently.
    """
    cache_path = _get_cache_path(standard_full)
    
    if _is_cache_valid(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("results", [])
        except Exception as e:
            logger.error(f"Failed to read cache {cache_path}: {e}")
            
    # Fetch live
    url = f"https://lims.bis.gov.in/home/search_is_number/?is_number__doc_no={is_number_val}"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        with httpx.Client(timeout=30.0, verify=False, headers=headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content = resp.text
            
            labs = _parse_lims_html(content, url)
            
            if not labs and "dataTable" not in content:
                # Likely blocked or captcha, raise exception to use cache instead of caching empty
                raise Exception("Failed to retrieve valid dataTable from LIMS.")
            
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source_url": url,
                    "results": labs
                }, f, indent=2)
                
            return labs
    except Exception as e:
        logger.error(f"Failed to fetch LIMS data from {url}: {e}")
        # Return stale cache if available
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("results", [])
            except Exception:
                pass
        return []

def _parse_lims_html(html_content: str, source_url: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # The table has multiple IDs in the raw HTML which might confuse some parsers, so we use class
    table = soup.find('table', class_='customTable')
    if not table:
        return results
        
    tbody = table.find('tbody')
    if not tbody:
        return results
        
    for tr in tbody.find_all('tr', recursive=False):
        # The modal inner tables mess up parsing if we recurse, and html.parser breaks on recursive=False 
        # due to malformed </th> instead of </td>. So we remove the modals first.
        for modal in tr.find_all('div', class_='modal'):
            modal.decompose()
            
        tds = tr.find_all(['td', 'th'])
        if len(tds) < 8:
            continue
            
        name = tds[1].get_text(strip=True)
        lab_code = tds[2].get_text(strip=True)
        standard = tds[3].get_text(strip=True)
        product = tds[4].get_text(strip=True)
        scope = tds[5].get_text(strip=True)
        
        testing_charges = tds[6].get_text(separator=' ', strip=True).strip()
        validity_date = tds[7].get_text(strip=True)
        remark = tds[8].get_text(strip=True) if len(tds) > 8 else ""
        
        # Check for suspended or derecognized
        full_text = f"{name} {scope} {remark}".lower()
        if "derecognized" in full_text or "suspended" in full_text:
            continue
            
        # Simple location extraction from name
        city = ""
        state = ""
        
        parts = [p.strip() for p in name.split(',')]
        if len(parts) > 1:
            city = parts[-1]
            
        results.append({
            "name": name,
            "lab_code": lab_code,
            "address": "", # Not easily available in this view
            "city": city,
            "state": state,
            "standard": standard,
            "product": product,
            "scope": scope,
            "testing_charges": testing_charges,
            "validity_date": validity_date,
            "source": "Bureau of Indian Standards",
            "source_url": source_url,
            "verification_status": "BIS LIMS"
        })
        
    return results

def filter_labs_by_location(labs: List[Dict[str, Any]], location: str) -> List[Dict[str, Any]]:
    if not location:
        return labs
    
    loc_lower = location.lower().strip()
    filtered = []
    for lab in labs:
        # Check name and city
        if loc_lower in lab.get("name", "").lower() or loc_lower in lab.get("city", "").lower():
            filtered.append(lab)
            
    return filtered
