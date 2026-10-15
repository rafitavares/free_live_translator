from __future__ import annotations

import re
import stat
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile


MAX_ARGOS_ARCHIVE_FILES = 10_000
MAX_ARGOS_UNCOMPRESSED_BYTES = 4 * 1024 * 1024 * 1024
MAX_ARGOS_COMPRESSION_RATIO = 1_000


def validate_argos_package_archive(path) -> None:
    """Reject unsafe or implausible Argos archives before its installer extracts them."""
    total_size = 0
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARGOS_ARCHIVE_FILES:
                raise ValueError("Argos package contains too many files.")
            for member in members:
                raw_name = member.filename.replace("\\", "/")
                parts = PurePosixPath(raw_name).parts
                if (
                    not raw_name
                    or raw_name.startswith("/")
                    or re.match(r"^[A-Za-z]:", raw_name)
                    or ".." in parts
                    or "\x00" in raw_name
                ):
                    raise ValueError(f"Argos package contains an unsafe path: {member.filename!r}")
                file_mode = (member.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(file_mode):
                    raise ValueError(f"Argos package contains a symbolic link: {member.filename!r}")
                if member.flag_bits & 0x1:
                    raise ValueError("Encrypted Argos packages are not supported.")
                total_size += member.file_size
                if total_size > MAX_ARGOS_UNCOMPRESSED_BYTES:
                    raise ValueError("Argos package expands beyond Church Cap's safety limit.")
                if (
                    member.file_size > 1024 * 1024
                    and member.compress_size > 0
                    and member.file_size / member.compress_size > MAX_ARGOS_COMPRESSION_RATIO
                ):
                    raise ValueError("Argos package has an unsafe compression ratio.")
    except BadZipFile as exc:
        raise ValueError("Downloaded Argos package is not a valid ZIP archive.") from exc
