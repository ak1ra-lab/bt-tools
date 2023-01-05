# coding: utf-8

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import bencodepy
from bencodepy.exceptions import BencodeDecodeError


def init_logger(name, level=logging.WARNING):
    format = "[%(asctime)s][%(levelname) 7s] %(name)s: %(message)s"
    logging.basicConfig(format=format, level=level, stream=sys.stderr)

    return logging.getLogger(name)


logger = init_logger("p2p_tools.torrent_relocate", logging.INFO)


def find_torrents(base_dir: Path, public: bool):
    torrents_grouped = {"private": {}, "public": {}}
    for root, _, files in os.walk(base_dir):
        root = root if isinstance(root, Path) else Path(root)
        for file in files:
            if not file.endswith(".torrent"):
                continue
            file = (root / file).expanduser()

            try:
                torrent = bencodepy.bread(file)
            except BencodeDecodeError as exc:
                logger.warning(f"file = {file} - {exc}")
                continue

            announce = torrent.get(b"announce", b"")
            if not announce:
                logger.warning(f"announce empty: file = {file}")
                continue

            logger.debug(f"file = {file}, announce = {announce}")
            announce_parsed = urlparse(announce.decode())
            netloc = announce_parsed.netloc.split(":")[0]

            torrent_type = "private" if torrent[b"info"].get(
                b"private", 0) else "public"

            if not netloc in torrents_grouped[torrent_type].keys():
                torrents_grouped[torrent_type][netloc] = []

            try:
                name = torrent[b"info"][b"name"].decode()
            except UnicodeDecodeError:
                try:
                    # 不知道有些种子中 name.utf-8 这个 key 是否符合 spec, 还是说是某些 client 的私有行为?
                    name = torrent[b"info"][b"name.utf-8"].decode()
                except KeyError as exc:
                    logger.warning(f"file = {file} - {exc}")
                    name = ""

            torrents_grouped[torrent_type][netloc].append(
                {"scheme": announce_parsed.scheme,
                    "name": name, "file": str(file)}
            )

    return torrents_grouped.pop("public") if public else torrents_grouped.pop("private")


def relocate_torrents(base_dir: Path, public: bool, dry_run: bool):
    base_dir = base_dir if isinstance(base_dir, Path) else Path(base_dir)
    torrents_grouped = find_torrents(base_dir, public)

    skipped_files = []
    for netloc, torrents in torrents_grouped.items():
        for torrent in torrents:
            src = Path(torrent["file"])
            if public:
                dest_dir = base_dir / torrent["scheme"]
            else:
                dest_dir = base_dir.parent / \
                    f"{base_dir.name}.pt" / torrent["scheme"] / netloc
            dest = dest_dir / src.name

            if not dest_dir.is_dir():
                if dry_run:
                    logger.info(f"os.makedirs('{dest_dir}')")
                else:
                    os.makedirs(dest_dir)

            if dest.is_file():
                logger.warning(f"dest = {dest} exists, skip...")
                skipped_files.append(str(src))
                continue

            if dry_run:
                logger.info(f"os.rename('{src}', '{dest}')")
                continue

            os.rename(src, dest)

    return skipped_files


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-b", "--base-dir", required=True,
                        help="base_dir for src torrents")
    parser.add_argument("-p", "--public", default=False, action="store_true",
                        help="find_torrents operation mode, public torrent if given, default is private")
    parser.add_argument("--dry-run", default=False, action="store_true",
                        help="dry run mode, preview files relocation")

    return parser.parse_args()


def main():
    args = parse_args()

    skipped_files = relocate_torrents(
        args.base_dir, public=args.public, dry_run=args.dry_run)

    logger.warning(json.dumps(skipped_files, ensure_ascii=False))


if __name__ == "__main__":
    main()
