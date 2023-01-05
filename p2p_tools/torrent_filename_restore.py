# coding: utf-8

import argparse
import os
import json
import logging
from pathlib import Path

from p2p_tools.utils import (
    init_logger,
    read_torrent,
    get_torrent_files
)


logger = init_logger("p2p_tools.torrent_filename_restore", logging.INFO)


def match_torrent_files(torrent: Path, base_dir: Path):
    torrent_name, torrent_dict = read_torrent(torrent)
    _, torrent_files = get_torrent_files(torrent_name, torrent_dict)

    for root, _, files in os.walk(base_dir):
        root = root if isinstance(root, Path) else Path(root)
        for file in files:
            file = (root / file).expanduser()
            for torrent_file in torrent_files:
                if not file.stat().st_size == torrent_file["length"]:
                    continue
                if not "matched_path" in torrent_file.keys():
                    torrent_file["matched_path"] = []
                torrent_file["matched_path"].append(str(file))

    return torrent_name, torrent_files


def rename_torrent_files(torrent: Path, base_dir: Path, dry_run):
    base_dir = base_dir if isinstance(base_dir, Path) else Path(base_dir)
    torrent_name, torrent_files = match_torrent_files(torrent, base_dir)
    torrent_dir = base_dir.parent / torrent_name

    skipped_files = []
    for file in torrent_files:
        if not "matched_path" in file.keys():
            logger.warning(f"{file['path']} has no match")
            skipped_files.append(file)
            continue
        if len(file["matched_path"]) > 1:
            logger.warning(
                f"{file['path']} has multiple matches {file['matched_path']}")
            skipped_files.append(file)
            continue

        src = base_dir / file["matched_path"][0]
        dest = torrent_dir / file["path"]

        if not dest.parent.is_dir():
            if dry_run:
                logger.debug(f"os.makedirs('{dest.parent}')")
            else:
                os.makedirs(dest.parent)

        if dest.is_file():
            logger.warning(f"{dest} exists, skip...")
            skipped_files.append(file)
            continue

        if dry_run:
            logger.debug(f"os.rename('{src}', '{dest}')")
            continue

        os.rename(src, dest)

    return skipped_files


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--torrent", required=True,
                        help="torrent file to read")
    parser.add_argument("-b", "--base-dir", required=True,
                        help="base_dir for altered torrent_files")
    parser.add_argument("--dry-run", default=False, action="store_true",
                        help="dry run mode, preview files to rename")

    return parser.parse_args()


def main():
    args = parse_args()

    skipped_files = rename_torrent_files(
        args.torrent, args.base_dir, args.dry_run)

    logger.warning("skipped_files = " +
                   json.dumps(skipped_files, ensure_ascii=False))


if __name__ == "__main__":
    main()
