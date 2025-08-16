from __future__ import annotations
from typing import Any, Dict, Optional, List
from src.supabase_client import get_supabase

def save_lead(*, name: Optional[str], email: str, phone: Optional[str], case_id: Optional[str], tag: Optional[str], payload: Dict[str, Any]) -> int:
    sb = get_supabase()
    data = {
        "name": name,
        "email": email,
        "phone": phone,
        "case_id": case_id,
        "tag": tag,
        "payload_json": payload,
    }
    res = sb.table("leads").insert(data).execute()
    return int(res.data[0]["id"])  # type: ignore

def list_leads(limit: int = 100) -> List[Dict[str, Any]]:
    sb = get_supabase()
    res = sb.table("leads").select("id,name,email,phone,case_id,tag,created_at").order("id", desc=True).limit(limit).execute()
    return list(res.data or [])  # type: ignore

def log_event(kind: str, *, ref_id: Optional[int] = None, note: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
    sb = get_supabase()
    sb.table("events").insert({
        "kind": kind,
        "ref_id": ref_id,
        "note": note,
        "payload_json": payload or {},
    }).execute()
