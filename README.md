
# bt-tools

## Install

```
git clone https://github.com/ak1ra-lab/bt-tools.git
cd bt-tools
python3 -m venv .venv
source .venv/bin/activate
pip3 install .
```

> 作为"不成器"的工具, 就不打算打包上传 PyPI 了

## [pt-login](bt_tools/pt_login.py)

由于各大 PT 站点都有特定期限内通过网页访问网站的要求,
故编写此脚本用于自动登录, 并将请求结果通过 Telegram bot 发送到自定义频道或群组中.

* `mkdir -p ~/.config/bt-tools && cp pt-login.json ~/.config/bt-tools/`
* 编辑 `~/.config/bt-tools/pt-login.json` 文件, 修改其中 `bot_token`, `chat_id`, 和各个 PT 站的 `cookies` 值
    * Telegram `bot_token` 可通过 [@BotFather](https://t.me/BotFather) 创建,
        * 创建 bot 后需添加到对应的 频道/群组 中, 添加到频道中需要 bot 为频道管理员, 权限允许消息发送即可
    * Telegram `chat_id` 可以是频道或群组, 公开 频道/群组 可直接使用其带 `@` 的 username,
    * 私有 频道/群组 可复制任意消息链接, 取其中第一组数字加上 `-100` 前缀,
        * 如消息 `https://t.me/c/1234567890/114514` 的 `chat_id` 为 `-1001234567890`
    * 如果示例配置文件中存在用户没有账号的站点, 可将相关站点整组配置删除
* 前面执行过 `source .venv/bin/activate` 的话, 配置好后可直接执行 `pt-login` 命令测试登录
* 添加定时任务需要指定 `.venv/bin/pt-login` 目录的绝对路径, 如 `5 0 * * * /path/to/bt-tools/.venv/bin/pt-login`

对于 [M-Team](https://kp.m-team.cc), 幸好这个站点没有登录验证码, 因此可以在 cookies 失效时通过用户名和密码请求
`/takelogin.php` 获取新的 cookies 并更新到配置文件中, 因此需要在配置文件中填入 M-Team 的 `username` 和 `password`.

而 [U2](https://u2.dmhy.org) 和 [Jpopsuki](https://jpopsuki.eu) 在登录时有验证码, 不过他们提供的
cookies 有效期相当长, 而验证码处理起来会麻烦些, 这里就先不做了, 在登录失败时可能需要手动更新下配置文件中的 cookies 相关值.

使用 `--help` 选项查看帮助信息: `pt-login --help`

## [torrent-filename-restore](bt_tools/torrent_filename_restore.py)

用于实现一个非常"小众"的需求, 对某个文件名被改乱的 Torrent 任务保存目录, 将其中的文件名还原为 .torrent 文件中结构.

> 因为 .torrent 文件只记录了每个文件的 大小 (length),
> 因此在尝试匹配时可能会出现某个文件被匹配多次, 对于这种情况会跳过对该文件的重命名.

使用 `--help` 选项查看帮助信息: `torrent-filename-restore --help`

## [torrent-relocate](bt_tools/torrent_relocate.py)

用于对提供的 `--base-dir` 目录下的 .torrent 文件分类整理,

* 对 public tracker 的种子移动到另一个目录, `dest_dir = f"{base_dir}.public/{scheme}"`
* 对 private tracker 的种子移动到另一个目录: `dest_dir = f"{base_dir}.private/{scheme}/{netloc}"`
* 分组的同时, 将 .torrent 文件名重命名为 `f"{torrent[b'info'][b'name']}".torrent`

因为取了 .torrent 文件内的 `name` 字段作为文件名, 在一定程度上可保证目标目录文件的唯一性,
当然也可能存在 `name` 字段重名时, 检测到目标文件存在时而被跳过的文件.

使用 `--help` 选项查看帮助信息: `torrent-relocate --help`

## [torrent-info](bt_tools/torrent_info.py)

读入 bencode 编码的文件, 如 .torrent 或 .fastresume 文件,
剔除掉一些在终端不可打印的 bytes 字段(如 `pieces`)后, 将结果打印在终端方便 debug 文件信息.

使用 `--help` 选项查看帮助信息: `torrent-info --help`

## See Also

* [bencode.py](https://pypi.org/project/bencode.py)
    * .torrent 文件和 qBittorrent 的 .fastresume 文件都是 bencode 编码
* [jslay88/qbt_migrate](https://github.com/jslay88/qbt_migrate)
    * 通过修改 qBittorrent 的 `BT_backup/*.fastresume` 文件的 `save_path` 快速迁移 qBittorrent 下载任务
