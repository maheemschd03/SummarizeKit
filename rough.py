# I AM Going to use it to hide the data while storing it in the DATABASE

from cryptography.fernet import Fernet

# Generate and store a key securely
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt
data = "<p>Sensitive User Data</p>"
encrypted_data = cipher.encrypt(data.encode())
print(f"Encrypted Data : {type(encrypted_data)}")

# Decrypt
decrypted_data = cipher.decrypt(encrypted_data).decode()
print(f"Decrypted data : {decrypted_data}")

# T