from __future__ import annotations

import unittest
import zipfile
from io import BytesIO

from app.services.strategies.parsing import ParsingStrategyFactory


class UploadSecurityTests(unittest.TestCase):
    def test_rejects_invalid_utf8_upload(self) -> None:
        parser = ParsingStrategyFactory().for_upload_name("coordenadas.csv")

        with self.assertRaisesRegex(ValueError, "Encoding invalido"):
            parser.parse(b"\xff\xfe\x00")

    def test_rejects_zip_path_traversal(self) -> None:
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../evil.shp", b"")

        parser = ParsingStrategyFactory().for_upload_name("shape.zip")
        with self.assertRaisesRegex(ValueError, "caminho interno inseguro"):
            parser.parse(archive.getvalue())


if __name__ == "__main__":
    unittest.main()
