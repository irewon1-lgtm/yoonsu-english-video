"""Build an authenticated album release. The content key is never written to the release."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import secrets
import struct
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CHUNK = 1024 * 1024
CATALOG_AAD = b"yoonsu-album-catalog-v1"
TAG = re.compile(r"album-v[1-9][0-9]{0,8}")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

def video_aad(tag, slug, size, index):
    return f"yoonsu-video-v1\n{tag}\n{slug}\n{size}\n{index}".encode()

def encrypt_video(source, dest, cipher, tag, slug):
    size = source.stat().st_size
    prefix = secrets.token_bytes(8)
    asset = slug + ".yvideo"
    with source.open("rb") as plain, (dest / asset).open("wb") as output:
        index = 0
        while block := plain.read(CHUNK):
            iv = prefix + struct.pack(">I", index)
            output.write(cipher.encrypt(iv, block, video_aad(tag, slug, size, index)))
            index += 1
    with source.open("rb") as plain:
        digest = hashlib.file_digest(plain, "sha256").hexdigest()
    return {"slug": slug, "bytes": size, "nonce": prefix.hex(), "asset": asset, "sha256": digest}

def pack(out, web, media, key, version, previous=None):
    tag = f"album-v{version}"
    if not TAG.fullmatch(tag):
        raise ValueError("Invalid release version")
    out.mkdir(parents=True, exist_ok=True)
    cipher = AESGCM(key)
    episodes = sorted(p.name for p in (web / "episodes").iterdir() if p.is_dir())
    for slug in episodes:
        if not SLUG.fullmatch(slug):
            raise ValueError("Invalid episode ID")
    old_covers = {}
    if previous:
        old = previous.read_bytes()
        with zipfile.ZipFile(io.BytesIO(cipher.decrypt(old[:12],old[12:],CATALOG_AAD))) as archive:
            prior = {m["slug"]:m for m in json.loads(archive.read("catalog.json"))["videos"]}
            for slug in prior:
                path = f"episodes/{slug}/cover.jpg"
                old_covers[slug] = archive.read(path)
    else:
        prior = {}
    videos = []
    for slug in episodes:
        source = media / slug / "film.mp4"
        if source.is_file():
            video = encrypt_video(source,out,cipher,tag,slug)
            video["tag"] = tag
        else:
            if slug not in prior:
                raise FileNotFoundError(source)
            video = prior[slug]
        videos.append(video)
        print(slug, video["bytes"], video["tag"], flush=True)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("catalog.json",json.dumps(
            {"schema":1,"version":version,"chunk":CHUNK,"videos":videos},separators=(",",":")))
        for file in sorted(web.rglob("*")):
            if file.is_file() and file.suffix in {".html",".js",".css"}:
                archive.write(file,file.relative_to(web))
        for slug in episodes:
            local = media/slug/"cover.jpg"
            path = f"episodes/{slug}/cover.jpg"
            if local.is_file():
                archive.write(local, path)
            else:
                archive.writestr(path, old_covers[slug])
    nonce = secrets.token_bytes(12)
    (out/"content.bundle").write_bytes(nonce+cipher.encrypt(nonce,payload.getvalue(),CATALOG_AAD))

def read_key(path):
    raw = path.read_bytes()
    key = raw if len(raw) == 32 else bytes.fromhex(raw.decode().strip())
    if len(key) != 32:
        raise ValueError("An owner-supplied 256-bit content key is required")
    return key

if __name__ == "__main__":
    arg = argparse.ArgumentParser()
    arg.add_argument("--version",type=int,required=True)
    arg.add_argument("--web",type=Path,default=Path("web"))
    arg.add_argument("--media",type=Path,required=True)
    arg.add_argument("--key",type=Path,required=True)
    arg.add_argument("--out",type=Path,required=True)
    arg.add_argument("--previous",type=Path)
    args=arg.parse_args()
    pack(args.out,args.web,args.media,read_key(args.key),
         args.version,args.previous)
