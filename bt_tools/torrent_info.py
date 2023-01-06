# coding: utf-8

import argparse
import json
import logging
from pathlib import Path

from bt_tools.utils import (
    init_logger,
    bencode_read,
    read_torrent,
    get_torrent_files
)


logger = init_logger("bt_tools.torrent_info", logging.INFO)


def dump_torrent_info(torrent: Path):
    torrent_name, torrent_dict = read_torrent(torrent)
    torrent_files = get_torrent_files(torrent_name, torrent_dict)

    # pop large object
    torrent_dict["info"].pop("pieces")
    try:
        torrent_dict["info"].pop("files")
    except KeyError:
        pass

    logger.info(f"torrent = {torrent}, torrent_name = {torrent_name}")
    for key, value in torrent_dict.items():
        logger.info(f"\t{key} = {value}")

    logger.info(f"\ttorrent_files = \n{json.dumps(torrent_files, indent=4, ensure_ascii=False)}")


def dump_fastresume(fastresume: Path):
    fastresume_dict = bencode_read(fastresume)

    # pop large object
    fastresume_dict.pop("pieces")

    logger.info(f"fastresume = {fastresume}")
    for key, value in fastresume_dict.items():
        logger.info(f"\t{key} = {value}")


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("files", nargs="+", metavar="file",
                        help="bencode encoded files to dump")

    return parser.parse_args()


def main():
    args = parse_args()
    bencode_files = args.files if isinstance(args.files, list) else []

    for bencode_file in bencode_files:
        if bencode_file.endswith(".torrent"):
            dump_torrent_info(bencode_file)
        elif bencode_file.endswith(".fastresume"):
            dump_fastresume(bencode_file)


if __name__ == "__main__":
    main()
