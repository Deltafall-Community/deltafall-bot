def fnv1a_64_signed(s: str) -> int:
    h = 0xcbf29ce484222325
    fnv_prime = 0x100000001b3
    for c in s.encode("utf-8"):
        h ^= c
        h = (h * fnv_prime) & 0xFFFFFFFFFFFFFFFF  # keep 64-bit
    # convert to signed 64-bit
    if h >= 0x8000000000000000:
        h -= 0x10000000000000000
    return h
