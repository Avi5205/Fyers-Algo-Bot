# ... (keep everything the same until line 275)

# REMOVE these two lines from FyersDataSocket initialization:
# run_background=False,  ❌ NOT SUPPORTED
# log_path=""            ❌ NOT SUPPORTED

# ✅ CORRECT initialization (around line 275):
self.ws = data_ws.FyersDataSocket(
    access_token=access_token
)
