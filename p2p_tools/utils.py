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


def bytes_dict_decode(bytes_dict: dict, encoding="utf-8", errors="ignore"):
    dict_decoded = {}
    for key, value in bytes_dict.items():
        if isinstance(key, bytes):
            key_decoded = key.decode(encoding, errors)
        else:
            key_decoded = key

        if isinstance(value, dict):
            value_decoded = bytes_dict_decode(value)
        elif isinstance(value, list):
            value_decoded = [
                v.decode(encoding, errors) if isinstance(v, bytes) else v for v in value]
        elif isinstance(value, bytes):
            value_decoded = value.decode(encoding, errors)
        else:
            value_decoded = value

        dict_decoded.update({key_decoded: value_decoded})

    return dict_decoded


def bencode_bread(bencode_file: Path):
    bencode_file = bencode_file \
        if isinstance(bencode_file, Path) else Path(bencode_file)
    bencode_dict = {}

    try:
        bencode_dict = bencodepy.bread(bencode_file)
    except BencodeDecodeError as exc:
        logger.warning(f"bencode_file = {bencode_file} - {exc}")

    return bencode_dict


def read_torrent(torrent: Path):
    torrent = torrent if isinstance(torrent, Path) else Path(torrent)
    torrent_dict = bencode_bread(torrent)

    torrent_name = ""
    if torrent_dict:
        try:
            torrent_name = torrent_dict[b"info"].get(b"name", b"").decode()
        except UnicodeDecodeError:
            # 不知道有些种子中 name.utf-8 这个 key 是否符合 spec, 还是说是某些 client 的私有行为?
            torrent_name = torrent_dict[b"info"].get(b"name.utf-8", b"").decode()
            # 如果没有 "name.utf-8" 字段, 则不对 name 进行 .decode()
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
