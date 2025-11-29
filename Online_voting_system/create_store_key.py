# create_store_key.py
from crypto_utils import generate_key, store_key_in_keyring

# You can change these names if needed
SERVICE_NAME = "online_voting_app"
USERNAME = "master_key"

key = generate_key()

ok = store_key_in_keyring(SERVICE_NAME, USERNAME, key)

if ok:
    print("===========================================")
    print(" SUCCESS: AES Key stored in OS Keyring")
    print("===========================================")
    print("Service Name :", SERVICE_NAME)
    print("Username     :", USERNAME)
    print("Key Length   :", len(key))
    print("-------------------------------------------")
    print("You can now run your voting system normally.")
    print("Templates will be encrypted automatically.")
else:
    print("====================================================")
    print(" FAILED to store key in OS keyring!")
    print("====================================================")
    print("Possible reasons:")
    print(" - 'keyring' is not installed     → pip install keyring")
    print(" - Your OS does not support keyring backend")
    print(" - You are running inside an environment without a keyring")
    print()
    print("Solution:")
    print(" - Use passphrase fallback in dframe (set USE_KEYRING=False)")
    print(" - Or install a compatible keyring backend for your OS")
