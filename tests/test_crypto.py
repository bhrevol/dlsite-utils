"""Cryptography tests."""
from dlsite_utils.crypto import CTCryptAES


def test_ctcrypt_aes_encrypt() -> None:
    """Encryption should succeed."""
    key = bytes.fromhex("06a9214036b8a15b512e03d534120006")
    iv = bytes.fromhex("3dafba429d9eb430b422da802c9fac41")
    plaintext = b"Single block msg"
    ciphertext = bytes.fromhex("e353779c1079aeb82708942dbe77181a")

    aes = CTCryptAES(key)
    assert ciphertext == aes.encrypt(plaintext, iv)


def test_ctcrypt_aes_decrypt() -> None:
    """Decryption should succeed."""
    key = bytes.fromhex("06a9214036b8a15b512e03d534120006")
    iv = bytes.fromhex("3dafba429d9eb430b422da802c9fac41")
    plaintext = b"Single block msg"
    ciphertext = bytes.fromhex("e353779c1079aeb82708942dbe77181a")

    aes = CTCryptAES(key)
    assert plaintext == aes.decrypt(ciphertext, iv)
