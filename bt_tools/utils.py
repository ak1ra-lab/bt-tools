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


logger = init_logger("bt_tools.utils", logging.INFO)


def bot_send_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    httpx.post(url, data=data)


def decode(item, encodings):
    # 这个函数的 encoding 不能 fallback 至 latin-1, 因为 latin-1 完全不会报错,
    # 而传入的对象(如 pieces 字段)确实是不能 decode 的 bytes stream, 这时需要保持 untouched
    for encoding in encodings:
        try:
            return item.decode(encoding)
        except UnicodeDecodeError as exc:
            slice = item[exc.start:exc.start+8]
            logger.debug(f"UnicodeDecodeError {slice}: {exc}")

    return item


def bytes_list_decode(bytes_list: list, encodings):
    decoded_list = []
    for item in bytes_list:
        if isinstance(item, list):
            decoded_list.append(bytes_list_decode(item, encodings))
        elif isinstance(item, dict):
            decoded_list.append(bytes_dict_decode(item, encodings))
        elif isinstance(item, bytes):
            decoded_list.append(decode(item, encodings))
        else:
            decoded_list.append(item)

    return decoded_list


def bytes_dict_decode(bytes_dict: dict, encodings):
    decoded_dict = {}
    for key, value in bytes_dict.items():
        key_decoded = decode(key, encodings) if isinstance(key, bytes) else key

        if isinstance(value, list):
            decoded_dict.update(
                {key_decoded: bytes_list_decode(value, encodings)})
        elif isinstance(value, dict):
            decoded_dict.update(
                {key_decoded: bytes_dict_decode(value, encodings)})
        elif isinstance(value, bytes):
            decoded_dict.update({key_decoded: decode(value, encodings)})
        else:
            decoded_dict.update({key_decoded: value})

    return decoded_dict


def bytes_obj_decode(bytes_obj, encodings):
    if isinstance(bytes_obj, list):
        return bytes_list_decode(bytes_obj, encodings)
    elif isinstance(bytes_obj, dict):
        return bytes_dict_decode(bytes_obj, encodings)
    elif isinstance(bytes_obj, bytes):
        return decode(bytes_obj, encodings)
    else:
        return bytes_obj


def bencode_read(bencode_file: Path, encodings: list = ["utf-8", "gb18030", "big5", "shift_jis"]):
    bencode_file = bencode_file \
        if isinstance(bencode_file, Path) else Path(bencode_file)
    bencode_dict = {}

    try:
        bencode_dict = bencodepy.bread(bencode_file)
    except BencodeDecodeError as exc:
        logger.warning(f"bencode_file = {bencode_file}, {exc}")

    # # 似乎 BitComet 在以其它 encoding 编码各字段时会加上 b"encoding" 字段标明编码方式
    # # 如果没有读取到 b"encoding" 字段, 则使用一组常用的 encodings, 最终传递给 decode() 函数
    # # 但是这样反而会使 BitComet 为非 UTF-8 编码字段而提供另一组带 .utf-8 后缀的字段 decode() 错误
    # # 比如用 GBK decode UTF-8 编码的 bytes:
    # #     b"\xe5\x9c\xa3\xe5\x9f\x8e\xe5\xae\xb6\xe5\x9b\xad".decode("gbk") 不会报错, 但结果是错的
    # encodings = [bencode_dict.get(b"encoding", b"").decode(), "utf-8"] \
    #     if bencode_dict.get(b"encoding") else ["utf-8", "gb18030", "big5", "shift_jis"]

    return bytes_dict_decode(bencode_dict, encodings)


def read_torrent(torrent: Path):
    torrent_dict = bencode_read(torrent)
    torrent_name = torrent_dict["info"].get("name") if torrent_dict else ""

    return torrent_name, torrent_dict


def get_torrent_files(torrent_name, torrent_dict):
    torrent_files = []

    # 对于单文件 .torrent, 不存在 "files" 字段
    files = torrent_dict["info"].get("files")
    if not files:
        torrent_files.append(
            {"length": torrent_dict["info"]["length"], "path": torrent_name})
    else:
        for file in files:
            torrent_files.append(
                {"length": file["length"], "path": os.path.sep.join(file["path"])})

    return torrent_files
