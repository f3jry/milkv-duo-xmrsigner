from __future__ import annotations
"""
OTS Exceptions
"""

class OtsException(Exception):
    pass

class OtsWalletAddressNotFoundException(OtsException):
    pass

class OtsPolyseedNoPasswordProvidedException(OtsException):
    pass

class OtsPolyseedChecksumMismatchException(OtsException):
    pass

class OtsSeedSeedDecodingFailedException(OtsException):
    pass

class OtsInvalidNetworkException(OtsException):
    pass

class OtsInvalidAddressException(OtsException):
    pass

class OtsTxSigningException(OtsException):
    pass
