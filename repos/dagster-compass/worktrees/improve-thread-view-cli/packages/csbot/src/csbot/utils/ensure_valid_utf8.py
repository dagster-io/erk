def ensure_valid_utf8(next_html: str) -> str:
    return next_html.encode("utf-8", errors="replace").decode("utf-8")
