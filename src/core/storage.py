import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import OutreachData

def save_outreach_data(data: OutreachData, base_dir: str = "data") -> str:
    """
    Saves the outreach data to a JSON file.
    Includes both a human-readable timestamp and a unix timestamp.
    """
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    
    now = datetime.now(timezone.utc)
    human_readable_ts = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    unix_ts = int(now.timestamp())
    
    payload = {
        "metadata": {
            "timestamp_human": human_readable_ts,
            "timestamp_unix": unix_ts
        },
        "data": data.to_dict()
    }
    
    safe_target_name = data.target_profile.first_name.lower().replace(" ", "_")
    safe_company_name = data.company_profile.company_name.lower().replace(" ", "_")
    filename = f"outreach_{safe_target_name}_{safe_company_name}_{unix_ts}.json"
    filepath = os.path.join(base_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
        
    return filepath
