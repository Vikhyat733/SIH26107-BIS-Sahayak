import re
from typing import Optional
from .bis_lims_service import search_labs_by_standard, filter_labs_by_location
from .standards_service import search_standards

def find_laboratories(query: Optional[str] = None, standard: Optional[str] = None, product: Optional[str] = None, location: Optional[str] = None):
    # Resolve the standard if we have a query or product
    resolved_standard = standard
    
    if not location and query:
        m = re.search(r'\b(?:near|in|at)\s+([a-zA-Z]+)', query, re.IGNORECASE)
        if m:
            location = m.group(1).title()

    if not resolved_standard:
        # e.g. "TMT reinforcement bars"
        search_term = product or query or ""
        if search_term:
            standards = search_standards(search_term)
            if standards and standards[0].get("score", 0) > 80:
                resolved_standard = standards[0].get("standard", "")

    # Extract IS number (e.g. IS 1786:2008 -> 1786)
    is_number_val = ""
    if resolved_standard:
        m = re.search(r'(?:IS[\s:-]*)(\d+)', resolved_standard, re.IGNORECASE)
        if m:
            is_number_val = m.group(1)
    elif query or product:
        m = re.search(r'(?:IS[\s:-]*)(\d+)', (query or "") + " " + (product or ""), re.IGNORECASE)
        if m:
            is_number_val = m.group(1)
            resolved_standard = f"IS {is_number_val}"

    if not is_number_val:
        return {
            "results": [],
            "message": "No verified laboratory result was found for this query."
        }

    # Fetch from LIMS
    labs = search_labs_by_standard(is_number_val, resolved_standard)
    
    if not labs:
        return {
            "results": [],
            "message": "No verified laboratory result was found for this query.",
            "extracted_standard": resolved_standard,
            "extracted_location": location
        }
        
    # Apply location filtering if needed
    if location:
        labs_filtered = filter_labs_by_location(labs, location)
        # We don't discard the rest, we just mark or return the location so the frontend knows what was matched.
        # Actually, since we need to show BOTH, we will return ALL labs, but return the extracted location.
        # The frontend will handle grouping into 'Labs matching [Location]' and 'Other labs'
        return {
            "results": labs,
            "message": f"Showing BIS LIMS laboratories matching {resolved_standard} near {location}.",
            "extracted_standard": resolved_standard,
            "extracted_location": location
        }

    return {
        "results": labs,
        "message": f"Found {len(labs)} BIS laboratory records for {resolved_standard}",
        "extracted_standard": resolved_standard,
        "extracted_location": location
    }
