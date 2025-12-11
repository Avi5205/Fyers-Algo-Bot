#!/usr/bin/env python3
import asyncio
import time
from datetime import datetime

async def monitor():
    print("🎯 HIGH-PROBABILITY MONITOR STARTED")
    print("Press Ctrl+C to stop")
    print()
    
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scanning...")
            
            # Run your high-probability scan here
            # (Use the logic from above)
            
            # Wait 5 minutes
            await asyncio.sleep(300)
            
        except KeyboardInterrupt:
            print("\n✅ Monitor stopped")
            break

if __name__ == "__main__":
    asyncio.run(monitor())
