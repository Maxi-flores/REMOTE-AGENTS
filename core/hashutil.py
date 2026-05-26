def fnv1a_32(text: str) -> str:
    """
    Deterministic, zero-dependency hash for telemetry signing.
    Returns an 8-hex-character lowercase string.
    """
    h = 2166136261
    for b in text.encode("utf-8", errors="surrogatepass"):
        h ^= b
        h = (h * 16777619) & 0xFFFFFFFF
    return f"{h:08x}"
