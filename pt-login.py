# coding: utf-8

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import httpx


def init_logger(name, level=logging.WARNING):
    format = "[%(asctime)s][%(levelname) 7s] %(name)s: %(message)s"
    logging.basicConfig(format=format, level=level, stream=sys.stderr)

    return logging.getLogger(name)


logger = init_logger("pt-login", logging.INFO)


def bot_send_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    httpx.post(url, data=data)


def parse_args():
    parser = argparse.ArgumentParser()

    config_default = Path("~/.config/p2p-tools/pt-login.json")
    parser.add_argument("-c", "--config", default=config_default,
                        help="pt-login config to read, default: %(default)s")
    parser.add_argument("-r", "--retry-count", default=3,
                        help="HTTP request retry count when preceding request failed")

    return parser.parse_args()


def main():
    args = parse_args()

    config = args.config if isinstance(args.config, Path) else Path(args.Path)
    with open(config.expanduser()) as fp:
        config_contents = json.loads(fp.read())

    chat_id = config_contents["chat_id"]
    bot_token = config_contents["bot_token"]
    headers = config_contents["headers"]

    messages = [f"<b>{datetime.now().isoformat()}</b>\n"]
    for site, site_config in config_contents["sites"].items():
        url = site_config["url"]
        cookies = site_config["cookies"]
        headers.update({"referer": url})

        status_codes = []
        for _ in range(args.retry_count):
            try:
                logger.info(f"httpx.get('{url}', headers={headers})")
                resp = httpx.get(url, headers=headers, cookies=cookies)
                status_codes.append(resp.status_code)
            except httpx.HTTPError as exc:
                logger.warning(f"HTTP Exception for {exc.request.url} - {exc}")
                continue

            if resp.status_code == 200:
                messages.append(f"* <a href='{url}'>{site}</a> request ok!")
                break

        logger.info(f"status_codes = {status_codes}")
        if all(c != 200 for c in status_codes):
            messages.append(
                f"* <a href='{url}'>{site}</a> request failed in all {args.retry_count} retries, "
                f"status_codes: {', '.join(status_codes)}"
            )

    logger.info(f"messages -> {messages}")
    bot_send_message(bot_token, chat_id, "\n".join(messages))


if __name__ == "__main__":
    main()
