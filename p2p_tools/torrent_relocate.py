# coding: utf-8

import argparse
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

from p2p_tools.utils import (
    init_logger,
    read_torrent
)


logger = init_logger("p2p_tools.torrent_relocate", logging.INFO)


def find_torrents(base_dir: Path, public: bool):
    torrents_grouped = {"private": {}, "public": {}}
    for root, _, files in os.walk(base_dir):
        root = root if isinstance(root, Path) else Path(root)
        for file in files:
            if not file.endswith(".torrent"):
                continue
            file = (root / file).expanduser()

            torrent_name, torrent_dict = read_torrent(file)
            if not torrent_dict:
                continue

            announce = torrent_dict.get(b"announce", b"").decode()
            logger.debug(f"file = {file}, announce = {announce}")
            if not announce:
                logger.warning(f"file = {file} announce empty, skip...")
                continue

            torrent_type = "private" \
                if torrent_dict[b"info"].get(b"private", 0) else "public"
            netloc = urlparse(announce).netloc.split(":")[0]
            if not netloc in torrents_grouped[torrent_type].keys():
                torrents_grouped[torrent_type][netloc] = []

            torrents_grouped[torrent_type][netloc].append(
                {
                    "scheme": urlparse(announce).scheme,
                    "name": torrent_name, "file": file
                }
            )

    return torrents_grouped.pop("public") if public else torrents_grouped.pop("private")


def relocate_torrents(base_dir: Path, public: bool, dry_run: bool):
    base_dir = base_dir if isinstance(base_dir, Path) else Path(base_dir)
    torrents_grouped = find_torrents(base_dir, public)

    skipped_files = []
    for netloc, torrents in torrents_grouped.items():
        for torrent in torrents:
            src = torrent["file"] \
                if isinstance(torrent["file"], Path) else Path(torrent["file"])
            if public:
                dest_dir = base_dir.parent / \
                    f"{base_dir.name}.public" / torrent["scheme"]
            else:
                dest_dir = base_dir.parent / \
                    f"{base_dir.name}.private" / torrent["scheme"] / netloc
            dest = dest_dir / (f"{torrent['name']}.torrent"
                               if torrent["name"] else f"{src.name}.torrent")

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

    logger.warning(
        f"skipped_files = {json.dumps(skipped_files, indent=4, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
