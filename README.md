
# p2p-tools

## `pt-login.py`

由于各大 PT 站点都有特定期限内通过网页访问网站的要求,
故编写此脚本用于自动登录, 并将请求结果通过 Telegram bot 发送到自定义频道或群组中.

* `git clone https://github.com/ak1ra-lab/p2p-tools.git && cd p2p-tools`
* `pip3 install -r requirements.txt`
* `mkdir -p ~/.config/p2p-tools && cp pt-login.py pt-login.json ~/.config/p2p-tools/`
* 编辑 `~/.config/p2p-tools/pt-login.json` 文件, 修改其中 `bot_token`, `chat_id`, 和各个 PT 站的 `cookies` 值
    * Telegram `bot_token` 可通过 [@BotFather](https://t.me/BotFather) 创建,
        * 创建 bot 后需添加到对应的 频道/群组 中, 添加到频道中需要 bot 为频道管理员, 权限允许消息发送即可
    * Telegram `chat_id` 可以是频道或群组, 公开 频道/群组 可直接使用其带 `@` 的 username,
    * 私有 频道/群组 可复制任意消息链接, 取其中第一组数字加上 `-100` 前缀,
        * 如消息 `https://t.me/c/1234567890/114514` 的 `chat_id` 为 `-1001234567890`
    * 如果示例配置文件中存在用户没有账号的站点, 可将相关站点整组配置删除
* 配置好后可执行测试, 测试无误后添加定时任务, 如 `5 0 * * * python3 $HOME/.config/p2p-tools/pt-login.py`

对于 [M-Team](https://kp.m-team.cc), 幸好这个站点没有登录验证码, 因此可以在 cookies 失效时通过用户名和密码请求 `/takelogin.php` 获取新的 cookies 并更新到配置文件中, 因此需要在配置文件中填入 M-Team 的 `username` 和 `password`.

而 [U2](https://u2.dmhy.org) 和 [Jpopsuki](https://jpopsuki.eu) 在登录时有验证码, 不过他们提供的 cookies 有效期相当长, 而验证码处理起来会麻烦些, 这里就先不做了, 在登录失败时可能需要手动更新下配置文件中的 cookies 相关值.

## `torrent-name-restore.py`

用于实现一个非常"小众"的需求, 对某个文件名被改乱的 Torrent 任务保存目录, 将其中的文件名还原为 .torrent 文件中结构.

> 因为 .torrent 文件只记录了每个文件的 大小 (length),
> 因此在尝试匹配时可能会出现某个文件被匹配多次, 对于这种情况会跳过对该文件的重命名.

## `qbt-migrate.py`

本来还想写这样的一个工具用于修改 qBittorrent .fastresume 文件中的 save_path 和 qBt-savePath 用于快速迁移平台,
搜了下发现已经有人写过类似的工具, 参考 [jslay88/qbt_migrate](https://github.com/jslay88/qbt_migrate).

## reference

* [bencode.py](https://pypi.org/project/bencode.py)
    * .torrent 文件和 qBittorrent 的 .fastresume 文件都是 bencode 编码
* [jslay88/qbt_migrate](https://github.com/jslay88/qbt_migrate)
    * 用于 qBittorrent 任务迁移
