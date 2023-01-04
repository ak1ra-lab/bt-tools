# coding: utf-8

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from playwright.sync_api import sync_playwright
from cf_clearance import sync_cf_retry, sync_stealth


def init_logger(name, level=logging.WARNING):
    format = "[%(asctime)s][%(levelname) 7s] %(name)s: %(message)s"
    logging.basicConfig(format=format, level=level, stream=sys.stderr)

    return logging.getLogger(name)


logger = init_logger("pt-login", logging.DEBUG)


def bot_send_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    httpx.post(url, data=data)


def get_cookie_by_name(cookies, name):
    for cookie in cookies:
        if cookie.get("name") == name:
            return cookie.get("value")


def takelogin_playwright(site_config):
    url_parsed = urlparse(site_config["url"])
    url_login = f"{url_parsed.scheme}://{url_parsed.netloc}{site_config['login']}"
    url_takelogin = f"{url_parsed.scheme}://{url_parsed.netloc}{site_config['takelogin']}"
    credentials = site_config["credentials"]

    # 先访问 /login.php 拿到 cf_clearance cookies 和 user-agent header
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        sync_stealth(page, pure=True)
        page.goto(url_login)
        response = sync_cf_retry(page)
        if response:
            cf_clearance_value = get_cookie_by_name(
                page.context.cookies(), "cf_clearance")
            logger.debug(f"cf_clearance_value = {cf_clearance_value}")
            user_agent = page.evaluate('() => {return navigator.userAgent}')
            logger.debug(f"user_agent = {user_agent}")
        else:
            logger.warning(f"{url_login} cf challenge fail")
        browser.close()

    # 带上上面的值再访问 /takelogin.php 拿到 tp cookies
    cookies = {"cf_clearance": cf_clearance_value}
    headers = {"user-agent": user_agent, "referer": url_login}
    try:
        logger.debug(f"httpx.post('{url_takelogin}', data={credentials})")
        response = httpx.post(url_takelogin, data=credentials,
                              cookies=cookies, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning(f"HTTP Exception for {exc.request.url} - {exc}")

    cookies = {"tp": ""}
    headers.update({"referer": url_takelogin})
    if response.is_success or response.is_redirect:
        cookies.update({"tp": get_cookie_by_name(response.cookies, "tp")})

    return cookies, headers


def takelogin(site_config, cookies, headers):
    url_parsed = urlparse(site_config["url"])
    url_takelogin = f"{url_parsed.scheme}://{url_parsed.netloc}{site_config['takelogin']}"
    credentials = site_config["credentials"]

    try:
        logger.debug(f"httpx.post('{url_takelogin}', data={credentials})")
        response = httpx.post(url_takelogin, data=credentials,
                              cookies=cookies, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning(f"HTTP Exception for {exc.request.url} - {exc}")

    cookies = {"tp": ""}
    if response.is_success or response.is_redirect:
        logger.debug(
            f"response = {response}, location = {response.headers.get('location')}")
        cookies.update({"tp": get_cookie_by_name(response.cookies, "tp")})

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

            cookies.update({"cf_clearance": get_cookie_by_name(
                response.cookies, "cf_clearance")})
            cookies, _ = takelogin(site_config, cookies=cookies, headers=headers)
            # cookies, _ = takelogin_playwright(site_config)
            logger.debug(f"takelogin cookies = {cookies}")

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
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
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
