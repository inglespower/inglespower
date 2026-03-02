import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_minutes(phone):
    res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]["minutes_remaining"]
    return 0


def subtract_minute(phone):
    m = get_minutes(phone)
    if m > 0:
        supabase.table("minutes").update(
            {"minutes_remaining": m - 1}
        ).eq("phone_number", phone).execute()
        return True
    return False


def add_minutes(phone, minutes):
    res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
    if res.data and len(res.data) > 0:
        current = res.data[0]["minutes_remaining"]
        supabase.table("minutes").update(
            {"minutes_remaining": current + minutes}
        ).eq("phone_number", phone).execute()
    else:
        supabase.table("minutes").insert(
            {"phone_number": phone, "minutes_remaining": minutes}
        ).execute()
