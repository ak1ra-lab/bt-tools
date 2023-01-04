# coding: utf-8

import argparse
import os
import json
import logging
import sys
from pathlib import Path

import bencodepy


def init_logger(name, level=logging.WARNING):
    format = "[%(asctime)s][%(levelname) 7s] %(name)s: %(message)s"
    logging.basicConfig(format=format, level=level, stream=sys.stderr)

    return logging.getLogger(name)


logger = init_logger("torrent-name-restore", logging.INFO)


def get_torrent_files(torrent):
    torrent_dict = bencodepy.bread(torrent)
    torrent_name = torrent_dict[b'info'][b'name'].decode()

    def joinpath(path: list):
        return os.path.sep.join([p.decode() for p in path])

    torrent_files = []
    for file in torrent_dict[b'info'][b'files']:
        torrent_files.append(
            {"length": file[b"length"], "path": joinpath(file[b"path"])}
        )

    return torrent_name, torrent_files


def match_torrent_files(torrent, base_dir: Path):
    torrent_name, torrent_files = get_torrent_files(torrent)

    for root, _, files in os.walk(base_dir):
        root = root if isinstance(root, Path) else Path(root)
        for file in files:
            length = (root / file).stat().st_size
            for torrent_file in torrent_files:
                if not length == torrent_file["length"]:
                    continue
                if not "matched_path" in torrent_file.keys():
                    torrent_file["matched_path"] = []
                torrent_file["matched_path"].append(file)

    return torrent_name, torrent_files


def rename_torrent_files(torrent, base_dir: Path, dry_run):
    base_dir = base_dir if isinstance(base_dir, Path) else Path(base_dir)
    torrent_name, torrent_files = match_torrent_files(torrent, base_dir)
    torrent_dir = base_dir.parent / torrent_name

    skipped_torrent_files = []
    for file in torrent_files:
        if not "matched_path" in file.keys():
            logger.warning(f"{file['path']} has no match")
            skipped_torrent_files.append(file)
            continue
        if len(file["matched_path"]) > 1:
            logger.warning(
                f"{file['path']} has multiple matches {file['matched_path']}")
            skipped_torrent_files.append(file)
            continue

        src = base_dir / file["matched_path"][0]
        dest = torrent_dir / file["path"]

        if not dest.parent.is_dir():
            if not dry_run:
                os.makedirs(dest.parent)
        else:
            logger.debug(f"os.makedirs('{dest.parent}')")

        if not dest.is_file():
            if not dry_run:
                os.rename(src, dest)
            else:
                logger.info(f"os.rename('{src}', '{dest}')")
        else:
            logger.warning(f"{dest} exists, skip...")
            skipped_torrent_files.append(file)

    return skipped_torrent_files


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--torrent", required=True,
                        help="torrent file to read")
    parser.add_argument("-b", "--base-dir", required=True,
                        help="base_dir for altered torrent_files")
    parser.add_argument("--dry-run", default=False, action="store_true",
                        help="dry run mode, preview files to rename")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    skipped_torrent_files = rename_torrent_files(
        args.torrent, args.base_dir, args.dry_run)

    logger.warning("skipped_torrent_files = " +
                   json.dumps(skipped_torrent_files, ensure_ascii=False))
