import warnings

warnings.filterwarnings("ignore", message=".*NotOpenSSL.*")
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except ImportError:
    pass
