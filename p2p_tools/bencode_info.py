# coding: utf-8

import argparse
import json
import logging
from pathlib import Path

from p2p_tools.utils import (
    init_logger,
    bytes_dict_decode,
    bencode_bread,
    read_torrent,
    get_torrent_files
)


logger = init_logger("p2p_tools.torrent_info", logging.INFO)


def dump_torrent_info(torrent: Path):
    torrent_name, torrent_dict = read_torrent(torrent)
    _, torrent_files = get_torrent_files(torrent_name, torrent_dict)

    # pop large object
    torrent_dict[b"info"].pop(b"pieces")

    logger.info(
        f"torrent_name = {torrent_name}, "
        f"torrent_files = {json.dumps(torrent_files, indent=4, ensure_ascii=False)}"
    )
    logger.info(
        f"torrent_name = {torrent_name}, torrent_dict = {bytes_dict_decode(torrent_dict)}")


def dump_fastresume(fastresume: Path):
    fastresume_dict = bytes_dict_decode(bencode_bread(fastresume))

    # pop large object
    fastresume_dict.pop("pieces")

    save_path = fastresume_dict.pop("save_path")
    qBt_savePath = fastresume_dict.pop("qBt-savePath")
    logger.info(f"fastresume_dict = {fastresume_dict}")
    logger.info(f"save_path = {save_path}, qBt-savePath = {qBt_savePath}")


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
