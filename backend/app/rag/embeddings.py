import hashlib
import math
import re
from typing import Protocol


class EmbeddingModel(Protocol):
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class DeterministicHashEmbeddingModel:
    def __init__(self, dimensions: int = 16) -> None:
        if dimensions <= 0:
            raise ValueError('dimensions must be greater than zero')
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _tokens(text):
            digest = hashlib.sha256(token.encode('utf-8')).digest()
            index = int.from_bytes(digest[:4], byteorder='big') % self.dimensions
            sign = -1.0 if digest[4] % 2 else 1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [value / norm for value in vector]


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r'[a-zA-Z0-9가-힣]+', text.lower()) if len(token) >= 2]
