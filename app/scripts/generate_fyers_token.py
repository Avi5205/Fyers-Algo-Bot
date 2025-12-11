#!/usr/bin/env python3
"""
Fyers v3 token generation script.
Run this to get an access token and save it to .env
"""
import os
from fyers_apiv3 import fyersModel
from dotenv import load_dotenv

load_dotenv()


def generate_token():
    client_id = os.getenv("FYERS_CLIENT_ID")
    secret_key = os.getenv("FYERS_SECRET_KEY")
    redirect_uri = os.getenv("FYERS_REDIRECT_URI")

    if not all([client_id, secret_key, redirect_uri]):
        raise RuntimeError(
            "FYERS_CLIENT_ID, FYERS_SECRET_KEY, and FYERS_REDIRECT_URI must be set in .env"
        )

    # Step 1: Create session model
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )

    # Step 2: Generate auth URL
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
        return

    # Step 3: Set auth code and generate access token
    session.set_token(auth_code)
    
    try:
        response = session.generate_token()
    except Exception as e:
        print(f"\nError generating token: {e}")
        return

    if not isinstance(response, dict):
        print(f"\nUnexpected response from Fyers: {response}")
        return

    if "access_token" not in response:
        print(f"\nToken generation failed. Response: {response}")
        return

    access_token = response["access_token"]
    
    print("\n" + "="*70)
    print("SUCCESS!")
    print("="*70)
    print(f"\nAccess Token: {access_token}\n")
    
    # Step 4: Save to .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    try:
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
        
        print(f"Access token saved to: {env_path}")
        print("\nYou can now run your data downloaders and strategies.\n")
        
    except Exception as e:
        print(f"\nWarning: Could not update .env file: {e}")
        print("Please manually add this line to your .env file:")
        print(f'FYERS_ACCESS_TOKEN="{access_token}"')


if __name__ == "__main__":
    generate_token()
