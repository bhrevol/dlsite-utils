"""Crytography module."""

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7, PaddingContext


class CTCryptAES:
    """CypherTec AES encryption class.

    Args:
        key: AES key.

    Note:
        ctcrypt uses AES128 in CBC mode, with W3C padding applied to make any
        input data align to AES128 block sizes. Padding is always stripped
        before returning, so the padding method is not actually important.
    """

    def __init__(self, key: bytes):
        self.key = key
        self.algo = algorithms.AES(key)
        self._pad = PKCS7(self.algo.block_size)

    def _padder(self) -> PaddingContext:
        return self._pad.padder()

    def encrypt(
        self,
        data: bytes,
        iv: bytes | None = None,
    ) -> bytes:
        """CBC encrypt data.

        Args:
            data: Plaintext data.
            iv: CBC initialization vector.

        Returns:
            Encrypted ciphertext.
        """
        if iv is None:  # pragma: no cover
            iv = bytes([0] * 16)

        padder = self._padder()
        padded_data = padder.update(data)
        padded_data += padder.finalize()
        padding = len(padded_data) - len(data)

        cipher = Cipher(self.algo, modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data)
        ciphertext += encryptor.finalize()
        return ciphertext[:-padding]

    def decrypt(self, data: bytes, iv: bytes | None = None) -> bytes:
        """CBC decrypt data.

        Args:
            data: Ciphertext data.
            iv: CBC initialization vector.

        Returns:
            Decrypted plaintext.
        """
        if iv is None:  # pragma: no cover
            iv = bytes([0] * 16)

        padder = self._padder()
        padded_data = padder.update(data)
        padded_data += padder.finalize()
        padding = len(padded_data) - len(data)

        cipher = Cipher(self.algo, modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(padded_data)
        plaintext += decryptor.finalize()

        return plaintext[:-padding]
