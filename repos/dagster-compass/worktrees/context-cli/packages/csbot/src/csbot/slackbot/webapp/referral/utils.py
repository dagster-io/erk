import re


def is_valid_uuid_token(token):
    """
    Validates if a token matches the standard UUID format using regex.
    This regex specifically targets the 8-4-4-4-12 hexadecimal character
    grouping with hyphens.
    """
    pattern = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    return bool(pattern.match(token))


def is_valid_org_referral_token(uuid_string):
    """
    Validates if a token matches the pattern of our generated referral tokens for organizations.
    """
    pattern = re.compile(r"^[0-9a-zA-Z-]{0,6}[0-9a-fA-F]{4}$")
    return bool(pattern.match(uuid_string))


def is_valid_promo_token(uuid_string):
    """
    Validates if a token matches the pattern of our promo tokens.
    """
    pattern = re.compile(r"^[A-Z]{0,20}$")
    return bool(pattern.match(uuid_string))
