"""Minimal, dependency-free dBase III/IV (.dbf) reader.

Only what the Wenchuan dataset needs: the attribute tables shipped next to the
ESRI shapefiles (``Debris_flow_catchment.dbf``, ``Dataset2_damdata.dbf``).
Written by hand so the reproduction does not depend on ``pyshp``/``geopandas``
(see README "third-party code").
"""
from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass
class Field:
    name: str
    type: str
    length: int
    decimals: int


class DbfTable:
    """In-memory representation of one .dbf attribute table."""

    def __init__(self, path: str, encoding: str = "utf-8"):
        self.path = path
        self.encoding = encoding
        self.fields: list[Field] = []
        self.records: list[dict] = []
        self._read()

    # ------------------------------------------------------------------ io
    def _read(self) -> None:
        with open(self.path, "rb") as fh:
            blob = fh.read()

        (n_records,) = struct.unpack_from("<I", blob, 4)
        (header_size,) = struct.unpack_from("<H", blob, 8)
        (record_size,) = struct.unpack_from("<H", blob, 10)

        pos = 32
        while blob[pos] != 0x0D:
            raw = blob[pos : pos + 32]
            name = raw[:11].split(b"\x00", 1)[0].decode("ascii", "replace").strip()
            ftype = chr(raw[11])
            length = raw[16]
            decimals = raw[17]
            self.fields.append(Field(name, ftype, length, decimals))
            pos += 32

        offset = header_size
        for _ in range(n_records):
            chunk = blob[offset : offset + record_size]
            offset += record_size
            if not chunk or chunk[0:1] == b"*":  # deleted record
                continue
            rec: dict = {}
            cursor = 1
            for f in self.fields:
                raw = chunk[cursor : cursor + f.length]
                cursor += f.length
                text = raw.decode(self.encoding, "replace").strip()
                if f.type in ("N", "F"):
                    try:
                        rec[f.name] = float(text) if f.decimals else int(text)
                    except ValueError:
                        rec[f.name] = None if text == "" else text
                elif f.type == "L":
                    rec[f.name] = text.upper() in ("Y", "T")
                else:
                    rec[f.name] = text
            self.records.append(rec)

    # -------------------------------------------------------------- helpers
    def to_rows(self) -> list[dict]:
        return self.records

    def __len__(self) -> int:
        return len(self.records)

    def __repr__(self) -> str:
        cols = ", ".join(f.name for f in self.fields)
        return f"<DbfTable {self.path!r} n={len(self.records)} cols=[{cols}]>"


def read_dbf(path: str) -> DbfTable:
    """Read a .dbf, retrying with GBK when UTF-8 yields replacement chars."""
    table = DbfTable(path, encoding="utf-8")
    joined = "".join(str(r) for r in table.records)
    if "\ufffd" in joined:
        table = DbfTable(path, encoding="gbk")
    return table