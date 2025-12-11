#!/usr/bin/env python3
"""
Fyers v3 token generation script.
Run this to get an access token and save it to .env
"""
import os
import sys
from pathlib import Path
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

# Load from project root .env
env_path = Path("/app/.env")
load_dotenv(env_path)

def generate_token():
    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    redirect_uri = os.getenv("FYERS_REDIRECT_URI", "https://127.0.0.1:5000/")

    if not client_id or not secret_key:
        print("\n" + "="*70)
        print("ERROR: Missing Fyers Credentials")
        print("="*70)
        print("\nPlease add these to your .env file:")
        print("  FYERS_CLIENT_ID=your_client_id")
        print("  FYERS_SECRET_KEY=your_secret_key")
        print("  FYERS_REDIRECT_URI=https://127.0.0.1:5000/")
        print("\nThen try again or use option 2 to paste token manually.")
        print("="*70)
        sys.exit(1)

    # Create session
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )

    # Generate auth URL
    auth_url = session.generate_authcode()
    
    print("\n" + "="*70)
    print("FYERS TOKEN GENERATION")
    print("="*70)
    print("\n1) Open this URL in your browser:")
    print(f"\n   {auth_url}\n")
    print("2) Login to Fyers and authorize the app")
    print("3) You will be redirected to your redirect_uri with ?auth_code=...")
    print("4) Copy the 'auth_code' value from the URL and paste below\n")
    
    auth_code = input("Enter auth_code: ").strip()

    if not auth_code:
        print("\nError: No auth_code provided. Exiting.")
        sys.exit(1)

    # Set auth code and generate access token
    session.set_token(auth_code)
    
    try:
        response = session.generate_token()
    except Exception as e:
        print(f"\nError generating token: {e}")
        sys.exit(1)

    if not isinstance(response, dict) or "access_token" not in response:
        print(f"\nToken generation failed. Response: {response}")
        sys.exit(1)

    access_token = response["access_token"]
    
    print("\n" + "="*70)
    print("SUCCESS!")
    print("="*70)
    print(f"\nAccess Token: {access_token}\n")
    
    # Save to .env in project root
    try:
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            updated = False
            with open(env_path, "w") as f:
                for line in lines:
                    if line.startswith("FYERS_ACCESS_TOKEN="):
                        f.write(f'FYERS_ACCESS_TOKEN="{access_token}"\n')
                        updated = True
                    else:
                        f.write(line)
                
                if not updated:
                    f.write(f'\nFYERS_ACCESS_TOKEN="{access_token}"\n')
        else:
            with open(env_path, "w") as f:
                f.write(f'FYERS_ACCESS_TOKEN="{access_token}"\n')
        
        print(f"Access token saved to: {env_path}")
        
        # Save timestamp
        timestamp_file = Path("/app/.token_timestamp")
        with open(timestamp_file, "w") as f:
            from datetime import datetime
            f.write(datetime.now().strftime('%Y-%m-%d'))
        
        print("Token timestamp saved")
        print("\nYou can now continue with the trading system!\n")
        
    except Exception as e:
        print(f"\nWarning: Could not update .env file: {e}")
        print("Please manually add this line to your .env file:")
        print(f'FYERS_ACCESS_TOKEN="{access_token}"')

if __name__ == "__main__":
    generate_token()
