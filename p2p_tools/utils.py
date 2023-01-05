# coding: utf-8

import os
import logging
import sys
from pathlib import Path

import bencodepy
import httpx
from bencodepy.exceptions import BencodeDecodeError


def init_logger(name, level=logging.WARNING):
    format = "[%(asctime)s][%(levelname) 7s] %(name)s: %(message)s"
    logging.basicConfig(format=format, level=level, stream=sys.stderr)

    return logging.getLogger(name)


logger = init_logger("p2p_tools.utils", logging.INFO)


def bot_send_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    httpx.post(url, data=data)


def joinpath(path: list):
    return os.path.sep.join([p.decode() for p in path])


def read_torrent(torrent: Path):
    torrent = torrent if isinstance(torrent, Path) else Path(torrent)
    torrent_name = ""
    torrent_dict = {}

    try:
        torrent_dict = bencodepy.bread(torrent)
    except BencodeDecodeError as exc:
        logger.warning(f"torrent = {torrent} - {exc}")
        return torrent_name, torrent_dict

    try:
        torrent_name = torrent_dict[b"info"].get(b"name", b"").decode()
    except UnicodeDecodeError:
        # 不知道有些种子中 name.utf-8 这个 key 是否符合 spec, 还是说是某些 client 的私有行为?
        torrent_name = torrent_dict[b"info"].get(b"name.utf-8", b"").decode()
        # 如果没有 "name.utf-8" 字段, 则不对 name .decode()
        # 那么这里可能出现不知道怎么解码的 bytes, 几率很小
        if not torrent_name:
            torrent_name = torrent_dict[b"info"].get(b"name", b"")

    return torrent_name, torrent_dict


def get_torrent_files(torrent_name, torrent_dict):
    torrent_files = []

    # 对于单文件 .torrent, 不存在 b"files" 字段
    if not torrent_dict[b"info"].get(b"files"):
        torrent_files.append(
            {"length": torrent_dict[b"info"][b"length"], "path": torrent_name}
        )
    else:
        for file in torrent_dict[b"info"].pop(b"files"):
            torrent_files.append(
                {"length": file[b"length"], "path": joinpath(file[b"path"])}
            )

    return torrent_name, torrent_files


def dump_torrent_info(torrent):
    torrent_name, torrent_dict = read_torrent(torrent)
    _, torrent_files = get_torrent_files(torrent_name, torrent_dict)

    # pop large object
    torrent_dict[b"info"].pop(b"pieces")

    logger.info(
        f"torrent_name = {torrent_name}, torrent_files = {torrent_files}")
    logger.info(
        f"torrent_name = {torrent_name}, torrent_dict = {torrent_dict}")
