import os
import requests
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

EXOTEL_SID = os.getenv("EXOTEL_SID")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_AUTH_TOKEN = os.getenv("EXOTEL_AUTH_TOKEN")
EXOTEL_PHONE_NUMBER = os.getenv("EXOTEL_PHONE_NUMBER")

def make_outbound_call(customer_number: str, app_id: str):
    """
    Triggers an outbound call from Exotel to the customer.
    When the customer picks up, it connects them to your Exotel Applet (which hits your FastAPI webhook).
    """
    if not EXOTEL_SID or not EXOTEL_API_KEY or not EXOTEL_AUTH_TOKEN:
        print("Error: EXOTEL_SID, EXOTEL_API_KEY, or EXOTEL_AUTH_TOKEN not set in .env")
        sys.exit(1)

    # Exotel Outbound Call API Endpoint
    url = f"https://api.exotel.com/v1/Accounts/{EXOTEL_SID}/Calls/connect.json"
    
    # Create variations of the CallerId to bypass Exotel's strict formatting rules
    base_number = EXOTEL_PHONE_NUMBER
    if base_number.startswith("0"):
        base_number = base_number[1:]
    elif base_number.startswith("+91"):
        base_number = base_number[3:]
    caller_id_variations = [
        EXOTEL_PHONE_NUMBER,         # 1. As provided in .env
        base_number,                 # 2. 10-digit format (e.g., 9513886363)
        f"+91{base_number}",         # 3. E.164 format (e.g., +919513886363)
        f"0{base_number}",           # 4. Indian STD format (e.g., 09513886363)
        None                         # 5. Omit completely (Exotel auto-assigns)
    ]
    
    # Remove duplicates but preserve order
    caller_id_variations = list(dict.fromkeys(caller_id_variations))
    
    print(f"Initiating call to {customer_number}...")
    print(f"Will attempt the following Caller ID formats to find the one Exotel accepts: {caller_id_variations}\n")
    
    for caller_id in caller_id_variations:
        data = {
            "From": customer_number,
            "Url": f"http://my.exotel.com/{EXOTEL_SID}/exoml/start_voice/{app_id}"
        }
        if caller_id is not None:
            data["CallerId"] = caller_id
        
        print(f"Trying Caller ID: {caller_id if caller_id else '[OMITTED]'} ...")
        response = requests.post(
            url,
            data=data,
            auth=(EXOTEL_API_KEY, EXOTEL_AUTH_TOKEN)
        )
        
        if response.status_code == 200:
            print("\n✅ Call successfully initiated! Your phone should ring shortly.")
            print(f"Accepted Caller ID format: {caller_id}")
            return
        else:
            print(f"❌ Failed. Status: {response.status_code} | Error: {response.json().get('RestException', {}).get('Message', '')}")
            
    print("\nAll Caller ID formats failed. Please double check that this Exotel Virtual Number belongs to the Account SID provided.")

if __name__ == "__main__":
    print("=== Exotel Outbound Dialer ===")
    
    # Get the number to call
    target_number = input("Enter your personal phone number (e.g., +919876543210): ").strip()
    
    # Get the Exotel App ID
    print("\nYou can find your App ID in the Exotel Dashboard under Applets (it's the number in the Applet URL).")
    applet_id = input("Enter your Exotel Applet ID: ").strip()
    
    if target_number and applet_id:
        make_outbound_call(target_number, applet_id)
    else:
        print("Error: Phone number and Applet ID are required.")
