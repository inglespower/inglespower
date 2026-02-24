from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_minutes(phone):
    res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
if res.data:
return res.data[0]["minutes_remaining"]
return 0

def add_minutes(phone, minutes):
res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
if res.data:
current = res.data[0]["minutes_remaining"]
supabase.table("minutes").update({"minutes_remaining": current + minutes}).eq("phone_number", phone).execute()
else:
supabase.table("minutes").insert({
"phone_number": phone,
"minutes_remaining": minutes
}).execute()

def subtract_minute(phone):
m = get_minutes(phone)
if m > 0:
supabase.table("minutes").update({"minutes_remaining": m - 1}).eq("phone_number", phone).execute()
return True
return False
