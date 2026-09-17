from pwdlib import PasswordHash
hasher = PasswordHash.recommended()
encoded = hasher.hash("a-long-example-passphrase")
print(hasher.verify("a-long-example-passphrase", encoded))
print(hasher.verify("wrong-passphrase", encoded))
other = hasher.hash("a-long-example-passphrase")
print(encoded != other)
