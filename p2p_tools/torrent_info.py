# coding: utf-8

import argparse
import logging

from p2p_tools.utils import (
    init_logger,
    dump_torrent_info
)


logger = init_logger("p2p_tools.torrent_info", logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("torrent", nargs="+",
                        help="torrent files to dump")

    return parser.parse_args()

def main():
    args = parse_args()

    torrents = args.torrent if isinstance(args.torrent, list) else []

    for torrent in torrents:
        dump_torrent_info(torrent)

if __name__ == "__main__":
    main()
