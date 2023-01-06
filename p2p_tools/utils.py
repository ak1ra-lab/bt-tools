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


def decode(item, encoding="utf-8"):
    try:
        return item.decode(encoding)
    except UnicodeDecodeError as e:
        logger.debug(f"UnicodeDecodeError: {e}")
        return item


def bytes_list_decode(bytes_list: list, encoding="utf-8"):
    decoded_list = []
    for item in bytes_list:
        if isinstance(item, list):
            decoded_list.append(bytes_list_decode(item, encoding))
        elif isinstance(item, dict):
            decoded_list.append(bytes_dict_decode(item, encoding))
        elif isinstance(item, bytes):
            decoded_list.append(decode(item))
        else:
            decoded_list.append(item)

    return decoded_list


def bytes_dict_decode(bytes_dict: dict, encoding="utf-8"):
    decoded_dict = {}
    for key, value in bytes_dict.items():
        key_decoded = decode(key) if isinstance(key, bytes) else key

        if isinstance(value, list):
            decoded_dict.update({key_decoded: bytes_list_decode(value)})
        elif isinstance(value, dict):
            decoded_dict.update({key_decoded: bytes_dict_decode(value)})
        elif isinstance(value, bytes):
            decoded_dict.update({key_decoded: decode(value)})
        else:
            decoded_dict.update({key_decoded: value})

    return decoded_dict


def bytes_obj_decode(bytes_obj, encoding="utf-8"):
    if isinstance(bytes_obj, list):
        return bytes_list_decode(bytes_obj, encoding)
    elif isinstance(bytes_obj, dict):
        return bytes_dict_decode(bytes_obj, encoding)
    elif isinstance(bytes_obj, bytes):
        return decode(bytes_obj, encoding)
    else:
        return bytes_obj


def bencode_read(bencode_file: Path):
    # read and decode all the items
    bencode_file = bencode_file \
        if isinstance(bencode_file, Path) else Path(bencode_file)
    bencode_dict = {}

    try:
        bencode_dict = bencodepy.bread(bencode_file)
    except BencodeDecodeError as exc:
        logger.warning(f"bencode_file = {bencode_file}, {exc}")

    return bytes_dict_decode(bencode_dict)


def read_torrent(torrent: Path):
    torrent = torrent if isinstance(torrent, Path) else Path(torrent)

    torrent_name = ""
    torrent_dict = bencode_read(torrent)
    if torrent_dict:
        torrent_name = torrent_dict["info"].get("name")
        # 如果 bencode_read 中 decode() name 字段失败, decode() 函数按原样返回 bytes,
        # 这时尝试读取另外一个"非标准"的 name.utf-8 字段, 这边如果真的是 utf-8 则肯定能 decode 成功,
        # 其实也可以使用另一种 encoding 来 decode(), 不过这样要猜测编码方式或者枚举几种常见的 encoding,
        # name.utf-8 字段不存在的情况下, torrent_name 返回值仍然有可能是 bytes, 那该怎么办呢?
        if isinstance(torrent_name, bytes):
            torrent_name = torrent_dict["info"].get("name.utf-8") \
                if torrent_dict["info"].get("name.utf-8") else torrent_dict["info"].get("name")

    return torrent_name, torrent_dict


def get_torrent_files(torrent_name, torrent_dict):
    torrent_files = []

    # 对于单文件 .torrent, 不存在 "files" 字段
    if not torrent_dict["info"].get("files"):
        torrent_files.append(
            {"length": torrent_dict["info"]["length"], "path": torrent_name})
    else:
        for file in torrent_dict["info"].get("files"):
            torrent_files.append(
                {"length": file["length"], "path": os.path.sep.join(file["path"])})

    return torrent_name, torrent_files
