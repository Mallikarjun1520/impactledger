import getpass
import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

if not supabase_url:
    print("ERROR: SUPABASE_URL is missing from .env")
    sys.exit(1)

if not supabase_anon_key:
    print("ERROR: SUPABASE_ANON_KEY is missing from .env")
    sys.exit(1)


email = input("Supabase test user email: ")
password = getpass.getpass("Supabase test user password: ")

url = f"{supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"

headers = {
    "apikey": supabase_anon_key,
    "Content-Type": "application/json",
}

payload = {
    "email": email,
    "password": password,
}


try:
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=15,
    )

    if response.status_code != 200:
        print("\nLogin failed:")
        print(f"Status: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()

    print("\nLogin successful.")
    print("\nAccess token:\n")
    print(data["access_token"])

except requests.RequestException as error:
    print(f"\nRequest failed: {error}")
    sys.exit(1)