# 14 — Authentication from zero: identity, passwords and sessions

[Previous](13-mongodb.md) · [Course map](00-course-guide.md) · [Next](15-tokens-and-authorization.md)

## Authentication versus authorization

**Authentication = Who are you?** Verify that the caller controls credentials associated with an identity. **Authorization = What are you allowed to do?** Check that identity's permissions for this particular action/resource. A hotel checks your ID at reception (authentication), then your key opens your room, not every room (authorization).

Neither Pydantic validation nor knowing a product ID proves permission. You can submit perfectly shaped malicious requests. CORS is not authentication either; we explain that browser feature separately.

## Registration and login: different operations

**Registration** creates an account record after validating identifiers, checking uniqueness, enforcing password policy and hashing the password. Real systems may also verify an email/phone, obtain consent and prevent automated abuse. Clients must not choose privileged roles or submit their own trusted verification status.

**Login** verifies credentials for an existing account, then issues proof usable on later requests. It should not create a new account automatically just because a username is unknown. Return a generic “invalid credentials” for unknown-user and wrong-password cases to reduce account enumeration (discovering which accounts exist). Rate-limit by multiple signals, not only username, and avoid permanently locking users out through an attacker-controlled counter.

## Why hash passwords instead of storing/encrypting them?

A password **hash** is a one-way derived value. Verification derives/checks the candidate using stored parameters rather than recovering the original password. **Encryption** is reversible using a key; password verification usually has no legitimate need to recover plaintext.

A **salt** is a random per-password value included in hashing. Two users with the same password should have different stored hashes. Modern password-hashing libraries generate and store salts/parameters inside the encoded hash. Do not manually remove that metadata or compare fresh randomized hash strings for equality.

General-purpose fast hashes such as SHA-256 are **not** appropriate password storage algorithms by themselves: attackers can test huge numbers of guesses quickly. **Argon2id** is a password-hashing algorithm designed to impose memory and computation costs. **pwdlib** is a Python library handling hashing/verification; its recommended configuration with the Argon2 extra uses modern password hashing. Benchmark cost settings under your real capacity. Hashing is intentionally expensive, so do not run it directly on an async event-loop thread.

## Complete hashing example

Install with `python -m pip install 'pwdlib[argon2]'`, then run `python examples/passwords.py`. This file does not start a web server and uses a demonstration password, not a production account.

## Example

### File: `examples/passwords.py`

```python
from pwdlib import PasswordHash
hasher = PasswordHash.recommended()
encoded = hasher.hash("a-long-example-passphrase")
print(hasher.verify("a-long-example-passphrase", encoded))
print(hasher.verify("wrong-passphrase", encoded))
other = hasher.hash("a-long-example-passphrase")
print(encoded != other)
```

## Code Explanation

### Line 1

Import password hashing and verification, rather than implementing cryptography yourself.

### Line 2

Choose the library's recommended installed password-hash configuration.

### Line 3

Generate a salt and derive a stored hash representation; do not store the plaintext instead.

### Line 4

Verify the correct candidate against the stored hash; expect True.

### Line 5

Verify an incorrect candidate; expect False.

### Line 6

Hash the same password again with a fresh random salt.

### Line 7

Expect True: distinct salts produce different encodings despite the same password.

## What happens internally?

The library generates random salt, derives the hash using its algorithm/cost parameters and creates an encoded string carrying what verification needs. Verify extracts those parameters, computes the candidate derivation and checks it safely. There is no decrypt-password step. A stolen password database is still dangerous: attackers can guess weak passwords offline. Hashing reduces damage; it does not make weak passwords unguessable.

When cost recommendations change, libraries can support verification plus rehash/upgrade on a successful login. Upgrade stored hashes using the successfully verified plaintext already present in that login request; do not ask users to reveal passwords through logs or support channels.

## Session versus token: what proves identity on later requests?

A **session** usually means server-side login state indexed by a random session ID. The browser often sends that ID in a cookie. The server looks it up and checks expiry/revocation. It is straightforward to revoke centrally, but every relevant request needs session access (possibly cached).

A **token** is a credential string the client presents. It may be opaque (meaningless without server lookup) or self-contained (such as a signed JWT containing claims). An opaque session ID is a kind of token too. Cookies versus headers describe **transport/storage**, while sessions versus self-contained tokens describe **state/verification**. These are not mutually exclusive categories.

For a traditional same-site web application, a secure server-side session cookie is often simpler than building JWT refresh infrastructure. Use a managed identity provider when account recovery, multi-factor authentication and enterprise integration would otherwise require inventing a security product.

## Browser credential storage and threats

**XSS (Cross-Site Scripting)** means attacker-controlled script runs in your application's browser origin. JavaScript-readable tokens in localStorage can be stolen by such script. **CSRF (Cross-Site Request Forgery)** tricks a browser into making an unwanted authenticated request using automatically attached credentials such as cookies.

Cookie flags help: `HttpOnly` prevents JavaScript reading the cookie; `Secure` sends it only over HTTPS; `SameSite` restricts cross-site sending with important browser/navigation exceptions. These flags are layers, not universal cures. Cookie-based state-changing operations need an appropriate CSRF strategy, such as a per-session CSRF token plus origin checks. XSS can still perform actions as a user even if it cannot read an HttpOnly cookie.

Do not put bearer credentials into query strings, analytics events or log messages. Do not assume HTTPS prevents a script already running in the client from stealing readable credentials. Choose storage and transport based on the actual client and threat model.

## Complete conceptual flow to implement next

```text
Register → validate account fields → hash password → persist account
Login → find account → verify password → issue short-lived access proof
Request → extract proof → verify integrity/expiry → load active identity
        → check permission and ownership → execute business operation
Expiry → validate refresh credential → rotate it → issue new access proof
Logout/compromise → revoke session/refresh family → apply access-token policy
```

A **refresh credential** has a narrower purpose: obtain new short-lived access credentials. Do not accept it at business endpoints. The next chapter implements these mechanics in a clearly marked local learning app.

## When to use / not use; common mistakes and best practices

Authenticate personal/private actions. A public product list may intentionally be anonymous. Do not require authentication just to make every route look secure, and do not omit it on a sensitive mutation because the UI hides the button.

Never store plaintext passwords, use reversible encryption as the default password store, log login bodies, hash with unsalted fast hashes, or let registration choose `admin`. Set both minimum and maximum accepted password lengths to manage abuse; do not silently truncate passwords. Offer MFA (Multi-Factor Authentication, proofs from different factor categories) and secure recovery for risk-sensitive systems. Recovery/reset tokens should be high-entropy, expiring, single-use and stored safely; reset should not email the old password.

## Practice

**Beginner:** Verify correct and incorrect passwords.
**Intermediate:** Explain why comparing `hash(password) == stored_hash` is wrong with random salts.
**Challenge:** Choose credentials for a same-site browser app versus a third-party API client.

## Expected Result / Solution

The complete example prints True, False, True. Intermediate: fresh hashing creates a new salt, so string equality does not represent verification; call `verify(candidate, stored)`.

Challenge: a same-site browser can use an HttpOnly/Secure/SameSite session cookie with CSRF protection and server revocation. A third-party client commonly uses an appropriately scoped access token in an Authorization header issued by a trusted authorization flow. Neither choice removes HTTPS, expiry, permission checks, abuse controls or secret redaction.

## Summary

Authentication proves identity, authorization checks actions, and password hashing limits breach damage. Token formats are one part of the wider login/session lifecycle—not the whole security system.
