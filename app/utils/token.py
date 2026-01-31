"""
Sub Gateway - Token 生成工具
"""
import secrets
import string


def generate_token(length: int = 32) -> str:
    """
    生成安全随机 token
    
    Args:
        length: token 长度，默认 32
    
    Returns:
        安全随机字符串
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))
