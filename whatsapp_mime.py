"""Small MIME adapter for the from_buffer/from_file API used by Neonize 0.10.

No native libmagic is needed. filetype is optional at import time so device
pairing remains available even before the extra media detector is installed.
"""
from pathlib import Path


def _guess(data):
    data = bytes(data[:8192])
    try:
        import filetype
        kind = filetype.guess(data)
        if kind:
            return kind.mime, kind.extension
    except ImportError:
        pass
    signatures = (
        (b'\xff\xd8\xff', 'image/jpeg', 'jpg'),
        (b'\x89PNG\r\n\x1a\n', 'image/png', 'png'),
        (b'GIF87a', 'image/gif', 'gif'), (b'GIF89a', 'image/gif', 'gif'),
        (b'%PDF-', 'application/pdf', 'pdf'),
        (b'PK\x03\x04', 'application/zip', 'zip'),
        (b'ID3', 'audio/mpeg', 'mp3'), (b'OggS', 'audio/ogg', 'ogg'),
    )
    for signature, mime, extension in signatures:
        if data.startswith(signature):
            return mime, extension
    if len(data) >= 12:
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'image/webp', 'webp'
        if data[4:8] == b'ftyp':
            return 'video/mp4', 'mp4'
    return 'application/octet-stream', 'data'


def from_buffer(buffer, mime=False):
    content_type, extension = _guess(buffer)
    return content_type if mime else extension


def from_file(filename, mime=False):
    with Path(filename).open('rb') as stream:
        return from_buffer(stream.read(8192), mime=mime)
