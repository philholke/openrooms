from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared rate limiter instance — must be the same object registered on
# app.state.limiter in main.py and used by route decorators.
limiter = Limiter(key_func=get_remote_address)
