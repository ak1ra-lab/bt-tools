# coding: utf-8

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from p2p_tools.utils import (
    init_logger,
    bot_send_message
)


logger = init_logger("p2p_tools.pt_login", logging.DEBUG)


def get_cookie_by_name(cookies, name):
    for cookie in cookies:
        if cookie.get("name") == name:
            return cookie.get("value")


def takelogin(site_config, cookies, headers, retry_count=3):
    url_parsed = urlparse(site_config["url"])
    url_takelogin = f"{url_parsed.scheme}://{url_parsed.netloc}{site_config['takelogin']}"
    credentials = site_config["credentials"]

    for _ in range(retry_count):
        try:
            logger.debug(f"httpx.post('{url_takelogin}', data={credentials})")
            response = httpx.post(url_takelogin, data=credentials,
                                  cookies=cookies, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning(f"HTTP Exception for {exc.request.url} - {exc}")
            continue

        cookies = {}
        if response.is_success or response.is_redirect:
            logger.debug(
                f"response = {response}, location = {response.headers.get('location')}")
            cookies.update({"tp": get_cookie_by_name(response.cookies, "tp")})
            break

    return cookies, headers


def pt_request(site_config, headers, args):
    config = args.config if isinstance(args.config, Path) else Path(args.Path)

    url = site_config["url"]
    cookies = site_config["cookies"]

    responses = []
    for _ in range(args.retry_count):
        try:
            logger.debug(f"httpx.get('{url}', cookies={cookies})")
            response = httpx.get(url, cookies=cookies, headers=headers)
            responses.append(response)
        except httpx.HTTPError as exc:
            logger.warning(f"HTTP Exception for {exc.request.url} - {exc}")
            continue

        if response.status_code == 200:
            break

        # cookies 失效跳转登录页, 尝试使用密码登录获取新 cookies 值
        if urlparse(url).netloc == "kp.m-team.cc" and response.is_redirect:
            logger.debug(
                f"response = {response}, location = {response.headers.get('location')}")

            cookies_takelogin = {}
            cf_clearance_value = get_cookie_by_name(
                response.cookies, "cf_clearance")
            if cf_clearance_value:
                logger.debug(
                    f"response = {response}, cf_clearance = {cf_clearance_value}")
                cookies_takelogin.update({"cf_clearance": cf_clearance_value})

            cookies, _ = takelogin(site_config, cookies=cookies_takelogin,
                                   headers=headers, retry_count=args.retry_count)
            logger.debug(f"takelogin returned cookies = {cookies}")

            if cookies.get("tp"):
                # 把重新获取的 cookies 写入配置文件 pt-login.json 中
                with open(config.expanduser(), "r") as fp:
                    config_contents = json.loads(fp.read())
                config_contents["sites"][urlparse(
                    url).netloc]["cookies"].update(cookies)
                with open(config.expanduser(), "w") as fp:
                    fp.write(json.dumps(config_contents,
                             indent=4, ensure_ascii=False))
            else:
                logger.warning(f"response = {response} takelogin failed")
                break

    return responses


def parse_args():
    parser = argparse.ArgumentParser()

    config_default = Path("~/.config/p2p-tools/pt_login.json")
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
    headers = {
        "user-agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    }

    messages = [f"<b>{datetime.now().isoformat()}</b>\n"]
    for site, site_config in config_contents["sites"].items():
        url = site_config["url"]
        responses = pt_request(site_config, headers, args)

        logger.debug(f"responses = {responses}")
        status_codes = [response.status_code for response in responses]
        # 任意一次 status_code 为 200 就认为请求成功
        if any(c == 200 for c in status_codes):
            messages.append(f"* <a href='{url}'>{site}</a> request ok!")
        else:
            messages.append(
                f"* <a href='{url}'>{site}</a> request failed in all {args.retry_count} retries, status_codes: {status_codes}"
            )

    logger.info(f"messages = {messages}")
    bot_send_message(bot_token, chat_id, "\n".join(messages))


if __name__ == "__main__":
    main()
