from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance globally
limiter = Limiter(key_func=get_remote_address)
