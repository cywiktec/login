import hashlib


class IntegrityChecker:
    @staticmethod
    def checksum(path):
        digest = hashlib.sha256()
        with open(path, "rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def verify(self, expected_checksums):
        return all(
            self.checksum(path) == expected
            for path, expected in expected_checksums.items()
        )
