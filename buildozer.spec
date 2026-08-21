[app]

# (str) 应用标题
title = 模拟炒股练习

# (str) 包名
package.name = stocksim

# (str) 包域名（反向域名，用于生成唯一应用ID）
package.domain = org.example

# (str) 源码目录
source.dir = .

# (list) 需要打包进 APK 的源码扩展名
source.include_exts = py,png,jpg,kv,atlas,ttf

# (str) 应用版本
version = 0.6

# (list) 依赖（本程序只用标准库 urllib + kivy，无需 requests）
requirements = python3,kivy

# (str) 屏幕方向：portrait（竖屏）/ landscape（横屏）
orientation = portrait

# (bool) 是否全屏
fullscreen = 0

# (list) 需要的安卓权限（联网获取行情）
android.permissions = INTERNET

# (int) 目标 Android API 版本
android.api = 33

# (int) 最低支持的 Android API 版本
android.minapi = 21

# (list) 支持的 CPU 架构（仅 arm64，覆盖几乎所有现代安卓手机，构建更快更稳）
android.archs = arm64-v8a

# (bool) 允许应用数据备份
android.allow_backup = True

# (bool) 自动接受安卓 SDK 许可协议（在 CI 无人值守环境下必须为 True）
android.accept_sdk_license = True

# 应用图标（用 logo 白背景竖版 生成）
icon.filename = %(source.dir)s/icon.png


[buildozer]

# (int) 日志级别：0=只错误 1=警告 2=信息
log_level = 2

# (bool) 以 root 运行时的警告
warn_on_root = 1
