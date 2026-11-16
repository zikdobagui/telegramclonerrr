"""CI smoke test: load the real Neonize binary with system libmagic unavailable.

Run in a fresh Python process from the repository root. Does not connect to WA.
"""
import builtins
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
original_import = builtins.__import__


def without_system_magic(name, *args, **kwargs):
    if name == 'magic' and 'magic' not in sys.modules:
        raise ImportError('System libmagic intentionally unavailable in this test')
    return original_import(name, *args, **kwargs)


builtins.__import__ = without_system_magic
from whatsapp_bridge import load_neonize_client

client_class = load_neonize_client()
import whatsapp_mime

assert sys.modules['magic'] is whatsapp_mime
assert whatsapp_mime.from_buffer(b'\x89PNG\r\n\x1a\n', mime=True) == 'image/png'
assert whatsapp_mime.from_buffer(b'\xff\xd8\xff\xe0', mime=True) == 'image/jpeg'
assert client_class.__name__ == 'NewClient'
print('PASS: real Neonize native core imported without system libmagic or .runtime build artifacts; no account connected')
