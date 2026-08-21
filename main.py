# -*- coding: utf-8 -*-
"""
============================================================
  模拟股票练习软件（虚拟交易 / 纯练习）
============================================================

  【重要免责声明】
  1. 本程序仅使用【完全虚拟的货币】进行股票交易逻辑练习，
     不涉及任何真实资金、真实证券账户、真实交易。
  2. 本程序【没有任何真实金融交易能力】，无法对接任何券商实盘。
  3. 行情数据来自公开免费接口，可能存在延迟或误差，仅供参考。
  4. 本程序不构成任何投资建议、荐股或收益承诺。
  5. 股市有风险，投资需谨慎。请勿据此进行真实交易决策。

  运行依赖：Python 3.8+  +  Kivy（无需 requests，网络用标准库 urllib）
  安装：pip install kivy
  运行：python stock_sim_game.py
============================================================
"""

import json
import os
import re
import sys
import random
import threading
import urllib.request
from datetime import datetime

# -------------------- Kivy 相关导入 --------------------
from kivy.app import App
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition


# ============================================================
# 一、全局配置（可自行修改）
# ============================================================

# 难度：名称 / 初始虚拟资金
DIFFICULTIES = {
    'easy': {'name': '简单', 'funds': 1_000_000},   # 100 万
    'hard': {'name': '困难', 'funds': 500_000},     # 50 万
    'hell': {'name': '地狱', 'funds': 300_000},     # 30 万
}

WIN_TARGET = 100_000_000.0      # 挑战成功目标：总资产达到 1 亿元
BANKRUPT_THRESHOLD = 100.0      # 总资产接近 0（<=100元）判定破产

# A股交易规则参数（可调）
LOT_SIZE = 100                  # 1 手 = 100 股
COMMISSION_RATE = 0.00025       # 佣金：万分之 2.5（买卖双向）
COMMISSION_MIN = 5.0            # 佣金最低 5 元/笔
STAMP_TAX_RATE = 0.0005         # 印花税：万分之 5（仅卖出收取）
TRANSFER_FEE_RATE = 0.00001     # 过户费：十万分之一（买卖双向）

REFRESH_INTERVAL = 30           # 行情自动刷新间隔（秒）

# 热门标的（用于快速选择 + 离线模式显示名称）
HOT_STOCKS = {
    '600519': '贵州茅台',
    '000001': '平安银行',
    '300750': '宁德时代',
    '601318': '中国平安',
    '000858': '五粮液',
    '600036': '招商银行',
}

# -------------------- 颜色主题（暗色） --------------------
# 注意：A股习惯“红涨绿跌”，买入按钮用红色、卖出按钮用绿色
C_BG       = (0.055, 0.086, 0.130, 1)   # 页面背景（深蓝黑）
C_CARD     = (0.118, 0.165, 0.227, 1)   # 卡片背景
C_CARD2    = (0.149, 0.200, 0.267, 1)   # 卡片背景（稍亮）
C_ACCENT   = (0.29, 0.51, 0.97, 1)      # 强调蓝
C_ACCENT_D = (0.22, 0.42, 0.85, 1)
C_GREEN    = (0.10, 0.78, 0.40, 1)      # 绿（跌/卖出）
C_GREEN_D  = (0.06, 0.62, 0.30, 1)
C_RED      = (1.00, 0.30, 0.30, 1)      # 红（涨/买入）
C_RED_D    = (0.82, 0.20, 0.20, 1)
C_GOLD     = (1.00, 0.84, 0.34, 1)      # 金色高亮
C_TEXT     = (0.92, 0.95, 0.98, 1)      # 主文字
C_SUB      = (0.62, 0.68, 0.75, 1)      # 次要文字
C_INPUT    = (0.09, 0.13, 0.19, 1)      # 输入框背景
C_TRACK    = (0.20, 0.26, 0.34, 1)      # 进度条底色


# ============================================================
# 二、工具函数
# ============================================================

def fmt(n):
    """金额格式化：千分位 + 两位小数"""
    try:
        return f"{float(n):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def rmb(n):
    """金额四舍五入到分"""
    return round(float(n) + 1e-9, 2)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def today():
    return datetime.now().strftime('%Y-%m-%d')


def find_cjk_font():
    """在常见路径中寻找支持中文的字体，用于 Kivy 显示中文。"""
    if sys.platform.startswith('win'):
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
        ]
    elif sys.platform == 'darwin':
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        ]
    else:  # Linux / Android
        candidates = [
            "/system/fonts/NotoSansCJK-Regular.ttc",
            "/system/fonts/DroidSansFallback.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


_CJK = find_cjk_font()
FONT_NAME = 'CJK' if _CJK else 'Roboto'
if _CJK:
    LabelBase.register(name='CJK', fn_regular=_CJK)


# ============================================================
# 三、行情服务（使用腾讯公开行情接口，免费、无需 Key）
# ============================================================

class Quote:
    """一条股票行情。"""
    def __init__(self, code, name, price, prev_close, open_price,
                 high, low, change, change_pct, limit_up, limit_down,
                 offline=False):
        self.code = code          # 6 位代码
        self.name = name          # 名称
        self.price = price        # 最新价
        self.prev_close = prev_close
        self.open = open_price
        self.high = high
        self.low = low
        self.change = change      # 涨跌额
        self.change_pct = change_pct
        self.limit_up = limit_up  # 涨停价
        self.limit_down = limit_down
        self.offline = offline    # 是否离线模拟数据


class QuoteService:
    """拉取沪深 A 股实时/当日行情。断网时提供离线模拟行情以便练习。"""
    API_HTTPS = "https://qt.gtimg.cn/q={}"
    API_HTTP = "http://qt.gtimg.cn/q={}"
    API_SINA = "https://hq.sinajs.cn/list={}"   # 备用源：新浪

    @staticmethod
    def resolve_symbol(code):
        """把用户输入（6位代码或带 sh/sz/bj 前缀）解析成市场+代码。"""
        c = str(code).strip().lower()
        for p in ('sh', 'sz', 'bj'):
            if c.startswith(p):
                c = c[len(p):]
                break
        c = c.replace('.', '')
        if len(c) != 6 or not c.isdigit():
            return None, None
        if c[0] == '6':
            return 'sh', 'sh' + c
        if c[0] in ('0', '3'):
            return 'sz', 'sz' + c
        if c.startswith(('43', '83', '87', '88', '92')):
            return 'bj', 'bj' + c
        if c.startswith('900'):
            return 'sh', 'sh' + c
        if c.startswith('200'):
            return 'sz', 'sz' + c
        return None, None

    @staticmethod
    def _request(symbols):
        """请求腾讯接口，https 优先，失败再试 http。返回 GBK 解码后的文本。"""
        for url_tpl in (QuoteService.API_HTTPS, QuoteService.API_HTTP):
            url = url_tpl.format(','.join(symbols))
            try:
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Referer': 'https://gu.qq.com/',
                })
                with urllib.request.urlopen(req, timeout=8) as resp:
                    return resp.read().decode('gbk', errors='ignore')
            except Exception:
                continue
        return None

    @staticmethod
    def _request_sina(symbols):
        """请求新浪接口（作为腾讯行情失效时的备用）。返回 GBK 解码后的文本。"""
        url = QuoteService.API_SINA.format(','.join(symbols))
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://finance.sina.com.cn',
            })
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.read().decode('gbk', errors='ignore')
        except Exception:
            return None

    @staticmethod
    def _calc_limits(name, code, prev_close):
        """根据板块/ST 计算涨跌停价（备用于接口未返回时）。"""
        if 'ST' in name.upper():
            rate = 0.05            # ST/*ST：±5%
        elif code.startswith(('300', '301', '688')):
            rate = 0.20            # 创业板 / 科创板：±20%
        else:
            rate = 0.10            # 主板：±10%
        return rmb(prev_close * (1 + rate)), rmb(prev_close * (1 - rate))

    @staticmethod
    def _parse_fields(f):
        """把腾讯返回的一个股票字段列表解析成 Quote。"""
        try:
            if len(f) < 35:
                return None
            name = f[1]
            code = f[2]
            price = float(f[3])
            prev = float(f[4])
            openp = float(f[5])
            high = float(f[33]) if len(f) > 33 and f[33] else prev
            low = float(f[34]) if len(f) > 34 and f[34] else prev
            change = float(f[31]) if len(f) > 31 and f[31] else (price - prev)
            pct = float(f[32]) if len(f) > 32 and f[32] else (
                (price - prev) / prev * 100 if prev else 0)
            lu = float(f[47]) if len(f) > 47 and f[47] else 0.0
            ld = float(f[48]) if len(f) > 48 and f[48] else 0.0
            if lu <= 0 or ld <= 0:
                lu, ld = QuoteService._calc_limits(name, code, prev)
            if price <= 0:
                return None  # 停牌/无有效价
            return Quote(code, name, price, prev, openp, high, low,
                         change, pct, lu, ld)
        except (ValueError, IndexError):
            return None

    @staticmethod
    def _parse(text):
        """解析接口返回文本，返回 {6位代码: Quote}。"""
        out = {}
        for m in re.finditer(r'v_(\w+)="([^"]*)"', text or ''):
            q = QuoteService._parse_fields(m.group(2).split('~'))
            if q:
                out[q.code] = q
        return out

    @staticmethod
    def _parse_sina(text):
        """解析新浪接口返回文本（备用），返回 {6位代码: Quote}。"""
        out = {}
        for m in re.finditer(r'var hq_str_(\w+)="([^"]*)"', text or ''):
            symbol = m.group(1)
            f = m.group(2).split(',')
            if len(f) < 6 or not f[0]:
                continue
            try:
                name = f[0]
                openp = float(f[1])
                prev = float(f[2])
                price = float(f[3])
                high = float(f[4])
                low = float(f[5])
            except (ValueError, IndexError):
                continue
            if price <= 0:
                continue
            code = symbol[2:]
            change = rmb(price - prev)
            pct = rmb(change / prev * 100) if prev else 0
            lu, ld = QuoteService._calc_limits(name, code, prev)
            out[code] = Quote(code, name, price, prev, openp, high, low,
                              change, pct, lu, ld)
        return out

    @staticmethod
    def offline_quote(code):
        """离线模拟行情：按代码+日期生成稳定价格，保证断网也能练习。"""
        seed = int(code) + int(datetime.now().strftime('%Y%m%d'))
        rnd = random.Random(seed)
        price = round(rnd.uniform(4.0, 200.0), 2)
        prev = round(price / (1 + rnd.uniform(-0.06, 0.06)), 2)
        prev = max(prev, 0.01)
        change = rmb(price - prev)
        pct = rmb(change / prev * 100) if prev else 0
        openp = round(prev * (1 + rnd.uniform(-0.03, 0.03)), 2)
        high = round(max(price, prev) * (1 + rnd.uniform(0, 0.02)), 2)
        low = round(min(price, prev) * (1 - rnd.uniform(0, 0.02)), 2)
        name = HOT_STOCKS.get(code, '股票' + code)
        lu, ld = QuoteService._calc_limits(name, code, prev)
        return Quote(code, name, price, prev, openp, high, low,
                     change, pct, lu, ld, offline=True)

    @staticmethod
    def fetch(code):
        """查询单只股票。返回 (Quote 或 None, 错误信息)。"""
        _, symbol = QuoteService.resolve_symbol(code)
        if not symbol:
            return None, "代码格式错误，请输入 6 位数字代码（如 600519）"
        # 腾讯优先，失败再试新浪
        text = QuoteService._request([symbol])
        if text is None:
            text = QuoteService._request_sina([symbol])
        if text is None:
            # 断网：返回离线模拟行情（离线标记= True）
            return QuoteService.offline_quote(symbol[2:]), "offline"
        q = QuoteService._parse(text).get(symbol[2:])
        if q is None:
            q = QuoteService._parse_sina(text).get(symbol[2:])
        if q:
            return q, None
        return None, "未找到该股票（代码不存在或已停牌）"

    @staticmethod
    def fetch_many(codes):
        """批量查询多只股票（用于刷新持仓价格）。断网返回空 dict。"""
        symbols = []
        for c in codes:
            _, s = QuoteService.resolve_symbol(c)
            if s:
                symbols.append(s)
        if not symbols:
            return {}
        text = QuoteService._request(symbols)
        if text is None:
            text = QuoteService._request_sina(symbols)
        if text is None:
            return {}
        data = QuoteService._parse(text)
        if not data:
            data = QuoteService._parse_sina(text)
        return data


# ============================================================
# 四、游戏核心逻辑（持仓 / 资金 / 交易规则）
# ============================================================

class Position:
    """单只股票的持仓。"""
    def __init__(self, code, name='', qty=0, sellable=0, cost=0.0,
                 last_price=0.0, locked=None):
        self.code = code
        self.name = name
        self.qty = qty            # 总持仓股数
        self.sellable = sellable  # 可卖股数（T+1 规则）
        self.cost = cost          # 总成本（含买入费用，摊薄成本）
        self.last_price = last_price
        self.locked = locked or {}  # {买入日期: 当日买入股数} 用于 T+1


class GameState:
    """一个存档：资金 + 持仓 + 日志。"""
    def __init__(self, difficulty='easy'):
        self.difficulty = difficulty
        self.start_funds = float(DIFFICULTIES[difficulty]['funds'])
        self.cash = self.start_funds
        self.positions = {}
        self.log = []
        self.trades = 0
        self.created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ---------- 买入 ----------
    def buy(self, code, name, price, qty):
        if qty <= 0 or qty % LOT_SIZE != 0:
            return False, f"买入数量必须是 100 股（1手）的整数倍"
        amount = price * qty
        comm = max(amount * COMMISSION_RATE, COMMISSION_MIN)
        transfer = amount * TRANSFER_FEE_RATE
        total = amount + comm + transfer
        if total > self.cash + 1e-6:
            return False, f"可用资金不足：需 {fmt(total)} 元，现有 {fmt(self.cash)} 元"
        self.cash = rmb(self.cash - total)
        pos = self.positions.get(code)
        if pos is None:
            pos = Position(code, name)
            self.positions[code] = pos
        pos.name = name
        pos.qty += qty
        pos.cost += amount + comm + transfer
        pos.last_price = price
        d = today()
        pos.locked[d] = pos.locked.get(d, 0) + qty   # 今日买入锁定（T+1）
        pos.sellable = pos.qty - sum(pos.locked.values())
        self.trades += 1
        avg = pos.cost / pos.qty
        self._log(f"买入 {name}({code}) {qty}股 @ {fmt(price)}  费用{fmt(comm+transfer)}  成本{fmt(avg)}")
        return True, f"买入成交：{name} {qty} 股，价格 {fmt(price)} 元"

    # ---------- 卖出 ----------
    def sell(self, code, price, qty):
        pos = self.positions.get(code)
        if pos is None:
            return False, "未持有该股票"
        if qty <= 0:
            return False, "卖出数量必须大于 0"
        if qty > pos.sellable:
            return False, f"可卖数量不足（T+1：今日买入次日才可卖）。当前可卖 {pos.sellable} 股"
        remaining = pos.qty - qty
        if remaining != 0 and remaining < LOT_SIZE:
            return False, f"零股须一次性卖出：请卖出全部 {pos.qty} 股"
        if qty % LOT_SIZE != 0 and qty != pos.qty:
            return False, "卖出数量须为 100 股整数倍（或一次性全部卖出）"
        amount = price * qty
        comm = max(amount * COMMISSION_RATE, COMMISSION_MIN)
        stamp = amount * STAMP_TAX_RATE
        transfer = amount * TRANSFER_FEE_RATE
        net = amount - comm - stamp - transfer
        self.cash = rmb(self.cash + net)
        avg = pos.cost / pos.qty
        pos.cost -= avg * qty
        pos.qty -= qty
        pos.last_price = price
        pos.sellable = pos.qty - sum(pos.locked.values())
        self.trades += 1
        pnl = (price - avg) * qty - (comm + stamp + transfer)
        if pos.qty == 0:
            del self.positions[code]
            self._log(f"卖出 {pos.name}({code}) {qty}股 @ {fmt(price)}  盈亏{fmt(pnl)}（清仓）")
            return True, f"卖出成交：{pos.name} {qty} 股，盈亏 {fmt(pnl)} 元（已清仓）"
        self._log(f"卖出 {pos.name}({code}) {qty}股 @ {fmt(price)}  盈亏{fmt(pnl)}")
        return True, f"卖出成交：{pos.name} {qty} 股，盈亏 {fmt(pnl)} 元"

    # ---------- T+1 解锁 ----------
    def refresh_sellable(self, d):
        for pos in self.positions.values():
            for k in [k for k in pos.locked if k < d]:
                del pos.locked[k]
            pos.sellable = pos.qty - sum(pos.locked.values())

    # ---------- 资产 ----------
    def market_value(self, prices):
        return sum(p.qty * (prices.get(p.code, p.last_price) or 0)
                   for p in self.positions.values())

    def total_assets(self, prices):
        return self.cash + self.market_value(prices)

    def _log(self, msg):
        ts = datetime.now().strftime('%m-%d %H:%M:%S')
        self.log.insert(0, f"[{ts}] {msg}")
        self.log = self.log[:200]

    # ---------- 存档 ----------
    def to_dict(self):
        return {
            'difficulty': self.difficulty,
            'start_funds': self.start_funds,
            'cash': self.cash,
            'trades': self.trades,
            'created_at': self.created_at,
            'log': self.log,
            'positions': {
                code: {
                    'code': p.code, 'name': p.name, 'qty': p.qty,
                    'sellable': p.sellable, 'cost': p.cost,
                    'last_price': p.last_price, 'locked': p.locked,
                } for code, p in self.positions.items()
            },
        }

    @classmethod
    def from_dict(cls, d):
        st = cls(d.get('difficulty', 'easy'))
        st.start_funds = float(d.get('start_funds', st.start_funds))
        st.cash = float(d.get('cash', st.cash))
        st.trades = int(d.get('trades', 0))
        st.created_at = d.get('created_at', st.created_at)
        st.log = list(d.get('log', []))
        for code, pd in (d.get('positions') or {}).items():
            st.positions[code] = Position(
                code=pd['code'], name=pd.get('name', ''),
                qty=int(pd['qty']), sellable=int(pd.get('sellable', 0)),
                cost=float(pd.get('cost', 0.0)),
                last_price=float(pd.get('last_price', 0.0)),
                locked=dict(pd.get('locked', {})),
            )
        return st


# ============================================================
# 五、自定义 UI 组件
# ============================================================

class Card(BoxLayout):
    """圆角卡片。"""
    bg = ListProperty(C_CARD)
    radius = ListProperty([14, 14, 14, 14])


class RButton(Button):
    """圆角按钮。"""
    bg = ListProperty(C_ACCENT)
    bg_down = ListProperty(C_ACCENT_D)
    radius = ListProperty([12, 12, 12, 12])


class HProgress(Widget):
    """水平进度条。"""
    value = NumericProperty(0.0)
    fill_color = ListProperty(C_GREEN)
    track_color = ListProperty(C_TRACK)


class Divider(Widget):
    """细分隔线。"""
    pass


class STextInput(TextInput):
    """带圆角背景的输入框。"""
    pass


class ScrollLabel(ScrollView):
    """可滚动长文本。"""
    text = StringProperty('')
    def on_text(self, *a):
        if 'lbl' in self.ids:
            self.ids.lbl.text = self.text


class PopupBox(BoxLayout):
    """弹窗内容容器：圆角卡片，默认填满弹窗。"""
    bg = ListProperty(C_CARD)
    radius = ListProperty([16, 16, 16, 16])


# ============================================================
# 六、界面布局（KV 语言）
# ============================================================

KV = '''
#:import dp kivy.metrics.dp

#:set BG (0.055, 0.086, 0.130, 1)
#:set CARD (0.118, 0.165, 0.227, 1)
#:set CARD2 (0.149, 0.200, 0.267, 1)
#:set ACCENT (0.29, 0.51, 0.97, 1)
#:set ACCENT_D (0.22, 0.42, 0.85, 1)
#:set GREEN (0.10, 0.78, 0.40, 1)
#:set GREEN_D (0.06, 0.62, 0.30, 1)
#:set RED (1.00, 0.30, 0.30, 1)
#:set RED_D (0.82, 0.20, 0.20, 1)
#:set GOLD (1.00, 0.84, 0.34, 1)
#:set TEXT (0.92, 0.95, 0.98, 1)
#:set SUB (0.62, 0.68, 0.75, 1)
#:set INPUT (0.09, 0.13, 0.19, 1)
#:set TRACK (0.20, 0.26, 0.34, 1)

# 全局中文字体（FONTREF 会在代码里被替换为 'CJK' 或 'Roboto'）
<Label>:
    font_name: FONTREF
<Button>:
    font_name: FONTREF
<TextInput>:
    font_name: FONTREF

<Card>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    padding: dp(14)
    spacing: dp(8)
    radius: [dp(14), dp(14), dp(14), dp(14)]
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            radius: self.radius
            pos: self.pos
            size: self.size

<RButton>:
    background_normal: ''
    background_down: ''
    background_color: (0, 0, 0, 0)
    color: (1, 1, 1, 1)
    bold: True
    font_size: dp(15)
    radius: [dp(12), dp(12), dp(12), dp(12)]
    canvas.before:
        Color:
            rgba: self.bg_down if self.state == 'down' else self.bg
        RoundedRectangle:
            radius: self.radius
            pos: self.pos
            size: self.size

<STextInput>:
    background_normal: ''
    background_active: ''
    background_color: (0, 0, 0, 0)
    foreground_color: TEXT
    hint_text_color: SUB
    cursor_color: ACCENT
    font_size: dp(15)
    multiline: False
    padding: dp(12), dp(14)
    canvas.before:
        Color:
            rgba: INPUT
        RoundedRectangle:
            radius: [dp(10), dp(10), dp(10), dp(10)]
            pos: self.pos
            size: self.size

<Divider>:
    size_hint_y: None
    height: dp(1)
    canvas:
        Color:
            rgba: (0.3, 0.38, 0.48, 0.5)
        Rectangle:
            pos: self.pos
            size: self.size

<HProgress>:
    size_hint_y: None
    height: dp(10)
    canvas.before:
        Color:
            rgba: self.track_color
        RoundedRectangle:
            radius: [self.height/2.0, self.height/2.0, self.height/2.0, self.height/2.0]
            pos: self.pos
            size: self.size
    canvas:
        Color:
            rgba: self.fill_color
        RoundedRectangle:
            radius: [self.height/2.0, self.height/2.0, self.height/2.0, self.height/2.0]
            pos: self.pos
            size: (self.width * self.value, self.height)

<ScrollLabel>:
    do_scroll_x: False
    bar_width: dp(6)
    Label:
        id: lbl
        text: root.text
        color: TEXT
        font_size: dp(14)
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width - dp(20), None
        halign: 'left'
        valign: 'top'

<PopupBox>:
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            radius: self.radius
            pos: self.pos
            size: self.size

<Root>:
    MenuScreen:
        name: 'menu'
    GameScreen:
        name: 'game'
    GameOverScreen:
        name: 'over'

# ---------------- 难度选择页 ----------------
<MenuScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(24)
        spacing: dp(16)
        size_hint: (0.9, 0.92)
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(92)
            spacing: dp(4)
            Label:
                text: '模拟炒股练习'
                font_size: dp(30)
                bold: True
                color: GOLD
                size_hint_y: None
                height: dp(48)
            Label:
                text: '虚拟资金 · 不涉及真实交易 · 仅用于练习交易逻辑'
                font_size: dp(13)
                color: SUB
                size_hint_y: None
                height: dp(22)
        RButton:
            text: '简单\\n初始虚拟资金 100 万元'
            bg: GREEN
            bg_down: GREEN_D
            font_size: dp(17)
            size_hint_y: None
            height: dp(78)
            on_release: app.choose_difficulty('easy')
        RButton:
            text: '困难\\n初始虚拟资金 50 万元'
            bg: (0.90, 0.62, 0.10, 1)
            bg_down: (0.75, 0.50, 0.06, 1)
            font_size: dp(17)
            size_hint_y: None
            height: dp(78)
            on_release: app.choose_difficulty('hard')
        RButton:
            text: '地狱\\n初始虚拟资金 30 万元'
            bg: RED
            bg_down: RED_D
            font_size: dp(17)
            size_hint_y: None
            height: dp(78)
            on_release: app.choose_difficulty('hell')
        RButton:
            id: continue_btn
            text: '暂无存档'
            bg: ACCENT
            bg_down: ACCENT_D
            size_hint_y: None
            height: dp(54)
            on_release: app.continue_game()
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: dp(42)
            spacing: dp(10)
            RButton:
                text: '交易规则'
                bg: CARD2
                bg_down: CARD
                font_size: dp(13)
                on_release: app.show_rules()
            RButton:
                text: '免责声明'
                bg: CARD2
                bg_down: CARD
                font_size: dp(13)
                on_release: app.show_disclaimer()
        Label:
            text: '行情数据来自公开接口，仅供参考 · 股市有风险'
            font_size: dp(11)
            color: SUB
            size_hint_y: None
            height: dp(20)

# ---------------- 主游戏页 ----------------
<GameScreen>:
    BoxLayout:
        orientation: 'vertical'
        # 顶部状态栏
        Card:
            id: status_card
            spacing: dp(6)
            padding: dp(12)
            BoxLayout:
                size_hint_y: None
                height: dp(32)
                Label:
                    id: difficulty_label
                    text: '简单'
                    color: GOLD
                    bold: True
                    font_size: dp(15)
                    size_hint_x: None
                    width: dp(76)
                    halign: 'left'
                    text_size: self.size
                RButton:
                    text: '刷新'
                    bg: CARD2
                    bg_down: CARD
                    font_size: dp(12)
                    size_hint_x: None
                    width: dp(80)
                    height: dp(30)
                    on_release: root.refresh_quotes()
                RButton:
                    text: '规则'
                    bg: CARD2
                    bg_down: CARD
                    font_size: dp(12)
                    size_hint_x: None
                    width: dp(56)
                    height: dp(30)
                    on_release: app.show_rules()
                RButton:
                    text: '菜单'
                    bg: CARD2
                    bg_down: CARD
                    font_size: dp(12)
                    size_hint_x: None
                    width: dp(56)
                    height: dp(30)
                    on_release: app.goto_menu()
            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    id: total_assets_label
                    text: '总资产 0.00 元'
                    font_size: dp(24)
                    bold: True
                    color: TEXT
                    halign: 'left'
            GridLayout:
                cols: 3
                size_hint_y: None
                height: dp(22)
                Label:
                    id: cash_label
                    text: '现金 --'
                    font_size: dp(12)
                    color: SUB
                    halign: 'left'
                Label:
                    id: mv_label
                    text: '市值 --'
                    font_size: dp(12)
                    color: SUB
                    halign: 'left'
                Label:
                    id: profit_label
                    text: '盈亏 --'
                    font_size: dp(12)
                    color: SUB
                    halign: 'left'
            HProgress:
                id: progress
            Label:
                id: progress_label
                text: '目标进度 0.00%'
                font_size: dp(11)
                color: SUB
                size_hint_y: None
                height: dp(18)
                halign: 'left'
        # 可滚动内容区
        ScrollView:
            id: scroll
            do_scroll_x: False
            bar_width: dp(6)
            BoxLayout:
                id: content
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(10)
                padding: dp(10)
                # 搜索
                Card:
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: dp(8)
                        size_hint_y: None
                        height: self.minimum_height
                        BoxLayout:
                            orientation: 'horizontal'
                            spacing: dp(8)
                            size_hint_y: None
                            height: dp(52)
                            Label:
                                id: search_display
                                text: '点击下方数字输入代码'
                                color: SUB
                                font_size: dp(17)
                                halign: 'left'
                                valign: 'middle'
                                size_hint_x: 1
                                text_size: self.width - dp(20), None
                                canvas.before:
                                    Color:
                                        rgba: INPUT
                                    RoundedRectangle:
                                        radius: [dp(10), dp(10), dp(10), dp(10)]
                                        pos: self.pos
                                        size: self.size
                            RButton:
                                id: search_btn
                                text: '搜索'
                                size_hint_x: None
                                width: dp(84)
                                on_release: root.do_search()
                        # 屏幕数字键盘：不依赖系统键盘，电脑手机都能用
                        GridLayout:
                            cols: 4
                            spacing: dp(6)
                            size_hint_y: None
                            height: dp(126)
                            RButton:
                                text: '1'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('1')
                            RButton:
                                text: '2'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('2')
                            RButton:
                                text: '3'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('3')
                            RButton:
                                text: '4'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('4')
                            RButton:
                                text: '5'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('5')
                            RButton:
                                text: '6'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('6')
                            RButton:
                                text: '7'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('7')
                            RButton:
                                text: '8'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('8')
                            RButton:
                                text: '9'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('9')
                            RButton:
                                text: '0'
                                bg: CARD2
                                bg_down: CARD
                                font_size: dp(15)
                                on_release: root.keypad_input('0')
                            RButton:
                                text: '删'
                                bg: ACCENT
                                bg_down: ACCENT_D
                                font_size: dp(15)
                                on_release: root.keypad_backspace()
                            RButton:
                                text: '清'
                                bg: ACCENT
                                bg_down: ACCENT_D
                                font_size: dp(15)
                                on_release: root.keypad_clear()
                # 热门标的
                Card:
                    Label:
                        text: '热门标的（点击快速选择）'
                        color: SUB
                        font_size: dp(12)
                        size_hint_y: None
                        height: dp(20)
                    GridLayout:
                        cols: 3
                        spacing: dp(6)
                        size_hint_y: None
                        height: dp(88)
                        RButton:
                            text: '贵州茅台\\n600519'
                            font_size: dp(12)
                            on_release: root.quick_search('600519')
                        RButton:
                            text: '平安银行\\n000001'
                            font_size: dp(12)
                            on_release: root.quick_search('000001')
                        RButton:
                            text: '宁德时代\\n300750'
                            font_size: dp(12)
                            on_release: root.quick_search('300750')
                        RButton:
                            text: '中国平安\\n601318'
                            font_size: dp(12)
                            on_release: root.quick_search('601318')
                        RButton:
                            text: '五粮液\\n000858'
                            font_size: dp(12)
                            on_release: root.quick_search('000858')
                        RButton:
                            text: '招商银行\\n600036'
                            font_size: dp(12)
                            on_release: root.quick_search('600036')
                # 交易面板
                Card:
                    id: trade_card
                    spacing: dp(6)
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(30)
                        Label:
                            id: quote_name
                            text: '——'
                            font_size: dp(18)
                            bold: True
                            color: TEXT
                            halign: 'left'
                            size_hint_x: 1
                        Label:
                            id: quote_offline
                            text: ''
                            color: (1.0, 0.6, 0.2, 1)
                            font_size: dp(12)
                            size_hint_x: None
                            width: dp(80)
                    Label:
                        id: quote_code
                        text: '输入代码后显示行情'
                        color: SUB
                        font_size: dp(13)
                        size_hint_y: None
                        height: dp(20)
                        halign: 'left'
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(44)
                        Label:
                            id: quote_price
                            text: '--'
                            font_size: dp(28)
                            bold: True
                            color: TEXT
                            halign: 'left'
                            size_hint_x: None
                            width: dp(150)
                        Label:
                            id: quote_change
                            text: '--'
                            font_size: dp(15)
                            halign: 'left'
                            valign: 'middle'
                    Label:
                        id: quote_hl
                        text: '今开 --  最高 --  最低 --'
                        color: SUB
                        font_size: dp(12)
                        size_hint_y: None
                        height: dp(18)
                        halign: 'left'
                    Label:
                        id: quote_limits
                        text: '涨停 --  跌停 --'
                        color: SUB
                        font_size: dp(12)
                        size_hint_y: None
                        height: dp(18)
                        halign: 'left'
                    # 买入
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: dp(6)
                        size_hint_y: None
                        height: self.minimum_height
                        Label:
                            text: '买入'
                            color: RED
                            bold: True
                            font_size: dp(15)
                            size_hint_y: None
                            height: dp(24)
                        BoxLayout:
                            size_hint_y: None
                            height: dp(24)
                            Label:
                                text: '现价'
                                color: SUB
                                size_hint_x: None
                                width: dp(60)
                                halign: 'left'
                            Label:
                                id: buy_price_label
                                text: '--'
                                color: TEXT
                                halign: 'left'
                        BoxLayout:
                            size_hint_y: None
                            height: dp(40)
                            spacing: dp(6)
                            STextInput:
                                id: buy_qty
                                hint_text: '数量(100的倍数)'
                                input_filter: 'int'
                                size_hint_x: 1
                            RButton:
                                text: '-100'
                                font_size: dp(12)
                                size_hint_x: None
                                width: dp(60)
                                on_release: root.qty_step('buy', -100)
                            RButton:
                                text: '+100'
                                font_size: dp(12)
                                size_hint_x: None
                                width: dp(60)
                                on_release: root.qty_step('buy', 100)
                        BoxLayout:
                            size_hint_y: None
                            height: dp(34)
                            spacing: dp(6)
                            RButton:
                                text: '半仓'
                                font_size: dp(12)
                                on_release: root.qty_fraction('buy', 0.5)
                            RButton:
                                text: '全仓买入'
                                font_size: dp(12)
                                on_release: root.qty_max('buy')
                        Label:
                            id: buy_est_label
                            text: '预计金额 0.00 元 · 费用约 0.00 元'
                            color: SUB
                            font_size: dp(12)
                            size_hint_y: None
                            height: dp(18)
                            halign: 'left'
                        RButton:
                            text: '买 入'
                            bg: RED
                            bg_down: RED_D
                            size_hint_y: None
                            height: dp(46)
                            on_release: root.do_buy()
                    Divider:
                    # 卖出
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: dp(6)
                        size_hint_y: None
                        height: self.minimum_height
                        Label:
                            text: '卖出'
                            color: GREEN
                            bold: True
                            font_size: dp(15)
                            size_hint_y: None
                            height: dp(24)
                        BoxLayout:
                            size_hint_y: None
                            height: dp(24)
                            Label:
                                text: '可卖'
                                color: SUB
                                size_hint_x: None
                                width: dp(60)
                                halign: 'left'
                            Label:
                                id: sellable_label
                                text: '0 股'
                                color: TEXT
                                halign: 'left'
                        BoxLayout:
                            size_hint_y: None
                            height: dp(40)
                            spacing: dp(6)
                            STextInput:
                                id: sell_qty
                                hint_text: '卖出数量'
                                input_filter: 'int'
                                size_hint_x: 1
                            RButton:
                                text: '-100'
                                font_size: dp(12)
                                size_hint_x: None
                                width: dp(60)
                                on_release: root.qty_step('sell', -100)
                            RButton:
                                text: '+100'
                                font_size: dp(12)
                                size_hint_x: None
                                width: dp(60)
                                on_release: root.qty_step('sell', 100)
                        BoxLayout:
                            size_hint_y: None
                            height: dp(34)
                            spacing: dp(6)
                            RButton:
                                text: '卖一半'
                                font_size: dp(12)
                                on_release: root.qty_fraction('sell', 0.5)
                            RButton:
                                text: '全部卖出'
                                font_size: dp(12)
                                on_release: root.qty_max('sell')
                        Label:
                            id: sell_est_label
                            text: '预计回收 0.00 元 · 费用约 0.00 元'
                            color: SUB
                            font_size: dp(12)
                            size_hint_y: None
                            height: dp(18)
                            halign: 'left'
                        RButton:
                            text: '卖 出'
                            bg: GREEN
                            bg_down: GREEN_D
                            size_hint_y: None
                            height: dp(46)
                            on_release: root.do_sell()
                # 持仓
                Card:
                    BoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(30)
                        Label:
                            text: '我的持仓'
                            bold: True
                            color: GOLD
                            font_size: dp(15)
                            size_hint_x: None
                            width: dp(130)
                            halign: 'left'
                        Label:
                            id: holdings_summary
                            text: ''
                            color: SUB
                            font_size: dp(12)
                            halign: 'right'
                    BoxLayout:
                        id: holdings_box
                        orientation: 'vertical'
                        spacing: dp(6)
                        size_hint_y: None
                        height: self.minimum_height
                    Label:
                        id: holdings_empty
                        text: '暂无持仓，搜索股票开始练习吧～'
                        color: SUB
                        font_size: dp(13)
                        size_hint_y: None
                        height: dp(30)
                        halign: 'left'
                # 交易记录
                Card:
                    Label:
                        text: '交易记录'
                        bold: True
                        color: GOLD
                        font_size: dp(15)
                        size_hint_y: None
                        height: dp(26)
                    BoxLayout:
                        id: log_box
                        orientation: 'vertical'
                        spacing: dp(2)
                        size_hint_y: None
                        height: self.minimum_height

# ---------------- 结算页 ----------------
<GameOverScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(20)
        size_hint: (0.9, 0.7)
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        Label:
            id: result_emoji
            text: '💥'
            font_size: dp(80)
            size_hint_y: None
            height: dp(100)
        Label:
            id: result_title
            text: '破产出局'
            font_size: dp(30)
            bold: True
            color: RED
            size_hint_y: None
            height: dp(46)
        Label:
            id: result_stats
            text: ''
            color: SUB
            font_size: dp(14)
            size_hint_y: None
            height: dp(130)
            halign: 'center'
            valign: 'top'
            text_size: self.width - dp(20), None
        RButton:
            text: '再来一局（同难度）'
            bg: ACCENT
            bg_down: ACCENT_D
            size_hint_y: None
            height: dp(52)
            on_release: app.replay()
        RButton:
            text: '返回主菜单'
            bg: CARD2
            bg_down: CARD
            size_hint_y: None
            height: dp(52)
            on_release: app.goto_menu()
'''


# ============================================================
# 七、页面逻辑
# ============================================================

class Root(ScreenManager):
    pass


class MenuScreen(Screen):
    def on_pre_enter(self):
        # 注意：初次构建时本页面可能尚未完成 ids 构建，
        # 故把读取存档按钮的逻辑延迟到下一帧执行。
        Clock.schedule_once(self._refresh_continue_btn, 0)

    def _refresh_continue_btn(self, *a):
        app = App.get_running_app()
        st = app.load_state()
        btn = self.ids.continue_btn
        if st:
            btn.disabled = False
            btn.opacity = 1
            btn.text = f'继续上次游戏（{DIFFICULTIES[st.difficulty]["name"]}）'
        else:
            btn.disabled = True
            btn.opacity = 0.35
            btn.text = '暂无存档'


class GameScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.price_cache = {}       # {代码: 最新价}
        self.current_quote = None   # 当前选中股票
        self.refresh_event = None
        self.game_ended = False
        self.search_code = ''       # 数字键盘输入的代码

    @property
    def app(self):
        return App.get_running_app()

    # ---------- 进入/离开页面 ----------
    def on_enter(self):
        self.game_ended = False
        self.current_quote = None
        self.price_cache = {}
        self.search_code = ''
        st = self.app.state
        if st:
            for code, p in st.positions.items():
                if p.last_price:
                    self.price_cache[code] = p.last_price
        self.refresh_ui()
        self.refresh_quotes()
        if self.refresh_event is None:
            self.refresh_event = Clock.schedule_interval(
                lambda dt: self.refresh_quotes(), REFRESH_INTERVAL)

    def on_leave(self):
        if self.refresh_event is not None:
            Clock.unschedule(self.refresh_event)
            self.refresh_event = None

    # ---------- 搜索 / 行情 ----------
    def do_search(self):
        code = (self.search_code or '').strip()
        if not code:
            self.app.notify('提示', '请先用数字键盘输入 6 位股票代码，例如 600519')
            return
        self.ids.search_btn.text = '搜索中...'
        self.fetch_quote_async(code, self._on_search)

    def quick_search(self, code):
        self.search_code = code
        self._update_search_display()
        self.do_search()

    # ---------- 屏幕数字键盘（不依赖系统键盘，Mac/安卓通用） ----------
    def _update_search_display(self):
        lbl = self.ids.search_display
        if self.search_code:
            lbl.text = self.search_code
            lbl.color = C_TEXT
        else:
            lbl.text = '点击下方数字输入代码'
            lbl.color = C_SUB

    def keypad_input(self, digit):
        if len(self.search_code) < 6:
            self.search_code += digit
            self._update_search_display()

    def keypad_backspace(self):
        self.search_code = self.search_code[:-1]
        self._update_search_display()

    def keypad_clear(self):
        self.search_code = ''
        self._update_search_display()

    def fetch_quote_async(self, code, callback):
        def work():
            q, err = QuoteService.fetch(code)
            Clock.schedule_once(lambda dt: callback(q, err), 0)
        threading.Thread(target=work, daemon=True).start()

    def _on_search(self, q, err):
        self.ids.search_btn.text = '搜索'
        if q is None:
            self.app.notify('获取行情失败', err or '未知错误')
            return
        self.current_quote = q
        self.price_cache[q.code] = q.price
        self.show_quote(q)
        if err == 'offline':
            self.app.notify('离线模式', '网络不可用，当前显示的是离线模拟行情数据。')

    def show_quote(self, q):
        self.ids.quote_name.text = q.name
        self.ids.quote_code.text = f"{q.code} · {'离线模拟数据' if q.offline else '真实行情'}"
        self.ids.quote_offline.text = '离线模拟' if q.offline else ''
        self.ids.quote_price.text = fmt(q.price)
        self.ids.buy_price_label.text = fmt(q.price)
        if q.change >= 0:  # A股：红涨绿跌
            self.ids.quote_price.color = C_RED
            self.ids.quote_change.color = C_RED
            self.ids.quote_change.text = f'+{fmt(q.change)}  +{q.change_pct:.2f}%'
        else:
            self.ids.quote_price.color = C_GREEN
            self.ids.quote_change.color = C_GREEN
            self.ids.quote_change.text = f'{fmt(q.change)}  {q.change_pct:.2f}%'
        self.ids.quote_hl.text = f'今开 {fmt(q.open)}  最高 {fmt(q.high)}  最低 {fmt(q.low)}'
        self.ids.quote_limits.text = f'涨停 {fmt(q.limit_up)}  跌停 {fmt(q.limit_down)}'
        pos = self.app.state.positions.get(q.code) if self.app.state else None
        self.ids.sellable_label.text = f"{pos.sellable if pos else 0} 股"
        self.update_est('buy')
        self.update_est('sell')

    # ---------- 数量快捷操作 ----------
    def _read_qty(self, panel):
        f = self.ids.buy_qty if panel == 'buy' else self.ids.sell_qty
        try:
            return int((f.text or '').strip())
        except ValueError:
            return 0

    def qty_step(self, panel, delta):
        f = self.ids.buy_qty if panel == 'buy' else self.ids.sell_qty
        v = max(0, self._read_qty(panel) + delta)
        f.text = str(v)
        self.update_est(panel)

    def qty_fraction(self, panel, frac):
        if not self.current_quote:
            self.app.notify('提示', '请先选择一只股票')
            return
        f = self.ids.buy_qty if panel == 'buy' else self.ids.sell_qty
        if panel == 'buy':
            base = self._max_buyable(self.current_quote.price)
            v = int(base * frac // LOT_SIZE) * LOT_SIZE
        else:
            pos = self.app.state.positions.get(self.current_quote.code)
            sellable = pos.sellable if pos else 0
            v = int(sellable * frac // LOT_SIZE) * LOT_SIZE
        f.text = str(v)
        self.update_est(panel)

    def qty_max(self, panel):
        if not self.current_quote:
            self.app.notify('提示', '请先选择一只股票')
            return
        f = self.ids.buy_qty if panel == 'buy' else self.ids.sell_qty
        if panel == 'buy':
            v = self._max_buyable(self.current_quote.price)
        else:
            pos = self.app.state.positions.get(self.current_quote.code)
            v = pos.sellable if pos else 0
        f.text = str(v)
        self.update_est(panel)

    def _max_buyable(self, price):
        """计算可用资金最多能买多少股（含费用）。"""
        if price <= 0:
            return 0
        cash = self.app.state.cash
        lots = int(cash // (price * LOT_SIZE))
        while lots > 0:
            qty = lots * LOT_SIZE
            amount = price * qty
            fee = max(amount * COMMISSION_RATE, COMMISSION_MIN) + amount * TRANSFER_FEE_RATE
            if amount + fee <= cash + 1e-6:
                return qty
            lots -= 1
        return 0

    def update_est(self, panel):
        if not self.current_quote:
            return
        price = self.current_quote.price
        qty = self._read_qty(panel)
        amount = price * qty
        if panel == 'buy':
            comm = max(amount * COMMISSION_RATE, COMMISSION_MIN) if amount > 0 else 0
            transfer = amount * TRANSFER_FEE_RATE
            self.ids.buy_est_label.text = f'预计金额 {fmt(amount)} 元 · 费用约 {fmt(comm + transfer)} 元'
        else:
            comm = max(amount * COMMISSION_RATE, COMMISSION_MIN) if amount > 0 else 0
            stamp = amount * STAMP_TAX_RATE
            transfer = amount * TRANSFER_FEE_RATE
            net = amount - comm - stamp - transfer
            self.ids.sell_est_label.text = f'预计回收 {fmt(net)} 元 · 费用约 {fmt(comm + stamp + transfer)} 元'

    # ---------- 交易 ----------
    def do_buy(self):
        st = self.app.state
        if st is None:
            return
        if not self.current_quote:
            self.app.notify('提示', '请先搜索并选择一只股票')
            return
        code = self.current_quote.code
        qty = self._read_qty('buy')
        if qty <= 0:
            self.app.notify('提示', '请输入买入数量（100 股整数倍）')
            return

        def cb(q, err):
            if q is None:
                self.app.notify('买入失败', err or '行情不可用')
                return
            if q.price >= q.limit_up - 0.001:
                self.app.notify('无法买入', f"{q.name} 已涨停（{fmt(q.price)}），涨停无法成交")
                return
            ok, msg = st.buy(code, q.name, q.price, qty)
            if ok:
                self.price_cache[code] = q.price
                self.current_quote = q
                self.show_quote(q)
                self.refresh_ui()
                self.app.save_state()
                self.app.notify('买入成功', msg)
            else:
                self.app.notify('买入失败', msg)
        self.fetch_quote_async(code, cb)

    def do_sell(self):
        st = self.app.state
        if st is None:
            return
        if not self.current_quote:
            self.app.notify('提示', '请先搜索并选择一只股票')
            return
        code = self.current_quote.code
        qty = self._read_qty('sell')
        if qty <= 0:
            self.app.notify('提示', '请输入卖出数量')
            return

        def cb(q, err):
            if q is None:
                self.app.notify('卖出失败', err or '行情不可用')
                return
            if q.price <= q.limit_down + 0.001:
                self.app.notify('无法卖出', f"{q.name} 已跌停（{fmt(q.price)}），跌停无法成交")
                return
            ok, msg = st.sell(code, q.price, qty)
            if ok:
                self.price_cache[code] = q.price
                self.current_quote = q
                self.show_quote(q)
                self.refresh_ui()
                self.app.save_state()
                self.app.notify('卖出成功', msg)
            else:
                self.app.notify('卖出失败', msg)
        self.fetch_quote_async(code, cb)

    def select_from_holding(self, code, action):
        """点击持仓行的买/卖按钮，把该股载入交易面板。"""
        def cb(q, err):
            if q is None:
                self.app.notify('提示', err or '行情不可用')
                return
            self.current_quote = q
            self.price_cache[code] = q.price
            self.show_quote(q)
            if action == 'sell':
                pos = self.app.state.positions.get(code)
                self.ids.sell_qty.text = str(pos.sellable if pos else 0)
                self.update_est('sell')
            else:
                self.ids.buy_qty.text = str(self._max_buyable(q.price))
                self.update_est('buy')
            self.ids.scroll.scroll_to(self.ids.trade_card)
        self.fetch_quote_async(code, cb)

    # ---------- 刷新 ----------
    def refresh_quotes(self):
        if self.game_ended or self.app.state is None:
            return
        codes = list(self.app.state.positions.keys())
        if self.current_quote and self.current_quote.code not in codes:
            codes.append(self.current_quote.code)
        if not codes:
            return

        def work():
            data = QuoteService.fetch_many(codes)
            Clock.schedule_once(lambda dt: self._apply_quotes(data), 0)
        threading.Thread(target=work, daemon=True).start()

    def _apply_quotes(self, data):
        changed = False
        for code, q in data.items():
            old = self.price_cache.get(code)
            self.price_cache[code] = q.price
            pos = self.app.state.positions.get(code)
            if pos:
                pos.last_price = q.price
            if old is None or abs(old - q.price) > 1e-6:
                changed = True
        if self.current_quote and self.current_quote.code in data:
            self.current_quote = data[self.current_quote.code]
            self.show_quote(self.current_quote)
        self.update_status()
        # 只有价格真的变化时才重建持仓列表，减少卡顿
        if changed:
            self.rebuild_holdings()

    # ---------- UI 刷新 ----------
    def refresh_ui(self):
        st = self.app.state
        if st is None:
            return
        st.refresh_sellable(today())
        self.update_status()
        self.rebuild_holdings()
        self.rebuild_log()
        if self.current_quote:
            pos = st.positions.get(self.current_quote.code)
            self.ids.sellable_label.text = f"{pos.sellable if pos else 0} 股"
        self.update_est('buy')
        self.update_est('sell')

    def update_status(self):
        st = self.app.state
        if st is None:
            return
        total = st.total_assets(self.price_cache)
        cash = st.cash
        mv = total - cash
        profit = total - st.start_funds
        self.ids.total_assets_label.text = f'总资产 {fmt(total)} 元'
        self.ids.cash_label.text = f'现金 {fmt(cash)}'
        self.ids.mv_label.text = f'市值 {fmt(mv)}'
        sign = '+' if profit >= 0 else ''
        self.ids.profit_label.text = f'盈亏 {sign}{fmt(profit)}'
        self.ids.profit_label.color = C_RED if profit >= 0 else C_GREEN
        self.ids.difficulty_label.text = DIFFICULTIES[st.difficulty]['name']
        progress = clamp(total / WIN_TARGET, 0.0, 1.0)
        self.ids.progress.value = progress
        self.ids.progress_label.text = f'目标 1 亿元 · 进度 {progress * 100:.2f}%'
        # 胜负判定
        if total >= WIN_TARGET:
            self.app.show_game_over(True, total)
        elif total <= BANKRUPT_THRESHOLD:
            self.app.show_game_over(False, total)

    def rebuild_holdings(self):
        box = self.ids.holdings_box
        box.clear_widgets()
        st = self.app.state
        if not st or not st.positions:
            self.ids.holdings_empty.opacity = 1
            self.ids.holdings_summary.text = ''
            return
        self.ids.holdings_empty.opacity = 0
        total_cost = 0.0
        total_mv = 0.0
        for code, pos in st.positions.items():
            price = self.price_cache.get(code, pos.last_price) or 0
            mv = pos.qty * price
            avg = pos.cost / pos.qty if pos.qty else 0
            pnl = (price - avg) * pos.qty
            pnl_pct = (price / avg - 1) * 100 if avg else 0
            total_cost += pos.cost
            total_mv += mv
            box.add_widget(self._holding_row(code, pos, price, avg, pnl, pnl_pct))
        self.ids.holdings_summary.text = f'市值 {fmt(total_mv)} · 盈亏 {fmt(total_mv - total_cost)}'

    def _mk_row_label(self, text, color=C_TEXT, bold=False, font_size=dp(12),
                      height=dp(18)):
        """持仓行内的文本标签：固定高度 + 超长自动省略号，绝不重叠。"""
        lbl = Label(text=text, color=color, bold=bold, font_size=font_size,
                    halign='left', valign='middle', size_hint_y=None,
                    size_hint_x=1, height=height, shorten=True)
        lbl.bind(width=lambda *a: setattr(lbl, 'text_size', (lbl.width, None)))
        return lbl

    def _holding_row(self, code, pos, price, avg, pnl, pnl_pct):
        card = Card(orientation='horizontal', padding=dp(10), spacing=dp(8), bg=C_CARD2)
        # 关键：两个子容器必须 size_hint_y=None，否则行高计算时不算内容 → 行太矮 → 文字溢出重叠
        info = BoxLayout(orientation='vertical', spacing=dp(2),
                         size_hint_x=1, size_hint_y=None)
        l1 = self._mk_row_label(f"{pos.name}  {code}", bold=True,
                                font_size=dp(14), height=dp(24))
        l2 = self._mk_row_label(f"持仓 {pos.qty} 股 · 可卖 {pos.sellable} 股",
                                color=C_SUB, height=dp(18))
        pcolor = C_RED if pnl >= 0 else C_GREEN
        l3 = self._mk_row_label(
            f"成本 {fmt(avg)} · 现价 {fmt(price)} · "
            f"盈亏 {('+' if pnl >= 0 else '')}{fmt(pnl)} ({('+' if pnl_pct >= 0 else '')}{pnl_pct:.2f}%)",
            color=pcolor, height=dp(18))
        info.add_widget(l1)
        info.add_widget(l2)
        info.add_widget(l3)
        btns = BoxLayout(orientation='vertical', spacing=dp(4),
                         size_hint_x=None, width=dp(60), size_hint_y=None)
        b1 = RButton(text='买', font_size=dp(12), size_hint_y=None,
                     height=dp(30), bg=C_RED, bg_down=C_RED_D)
        b1.bind(on_release=lambda *a, c=code: self.select_from_holding(c, 'buy'))
        b2 = RButton(text='卖', font_size=dp(12), size_hint_y=None,
                     height=dp(30), bg=C_GREEN, bg_down=C_GREEN_D)
        b2.bind(on_release=lambda *a, c=code: self.select_from_holding(c, 'sell'))
        btns.add_widget(b1)
        btns.add_widget(b2)
        card.add_widget(info)
        card.add_widget(btns)
        return card

    def rebuild_log(self):
        box = self.ids.log_box
        box.clear_widgets()
        if not self.app.state:
            return
        for line in self.app.state.log[:50]:
            lbl = Label(text=line, font_size=dp(11), color=C_SUB,
                        halign='left', size_hint_y=None, height=dp(18))
            lbl.text_size = (dp(300), None)
            lbl.shorten = True
            box.add_widget(lbl)


class GameOverScreen(Screen):
    pass


# ============================================================
# 八、主程序
# ============================================================

RULES_TEXT = (
    "· 交易品种：沪深 A 股（含主板、创业板、科创板）。\n"
    "· 资金：完全虚拟，不同难度初始资金不同。\n"
    "· 买卖单位：1 手 = 100 股；买入须为 100 股整数倍；卖出须为 100 股整数倍，"
    "零股（不足 100 股）须一次性卖出。\n"
    "· T+1 规则：当日买入的股票，下一交易日才可卖出。\n"
    "· 涨跌停：涨停无法买入，跌停无法卖出。\n"
    "· 手续费：佣金万分之 2.5（最低 5 元，买卖双向）；"
    "印花税万分之 5（仅卖出）；过户费十万分之一（买卖双向）。\n"
    "· 成交价：以最新行情价成交。\n"
    "· 胜负：总资产 ≥ 1 亿元 → 挑战成功；总资产 ≤ 100 元 → 破产失败。\n"
    "· 行情：使用真实当日行情；断网时自动切换为离线模拟数据。"
)

DISCLAIMER_TEXT = (
    "本软件为纯模拟练习工具，仅使用【完全虚拟的货币】进行股票交易逻辑练习。\n\n"
    "1. 不涉及任何真实资金、真实证券账户或真实交易；\n"
    "2. 无法对接任何券商实盘系统，不具备真实金融交易能力；\n"
    "3. 行情数据来自公开免费接口，可能有延迟或误差，仅供参考；\n"
    "4. 本软件不构成任何投资建议、荐股或收益承诺；\n"
    "5. 股市有风险，投资需谨慎。\n\n"
    "请理性练习，切勿据此进行真实交易决策。"
)


class StockSimApp(App):
    title = '模拟炒股练习'

    def build(self):
        # 重要：千万不要在这里设置 Window.size！
        # 安卓上强制设置窗口大小会导致界面只占屏幕一角、触摸坐标错乱。
        # 安卓端 Kivy 会自动使用全屏尺寸；桌面端使用默认窗口即可。
        Window.clearcolor = C_BG
        self.state = None
        Builder.load_string(KV.replace('FONTREF', repr(FONT_NAME)))
        self.sm = Root()
        self.sm.transition = FadeTransition(duration=0.25)
        return self.sm

    # ---------- 存档 ----------
    def save_path(self):
        base = self.user_data_dir or os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, 'stock_sim_save.json')

    def has_save(self):
        return os.path.exists(self.save_path())

    def save_state(self):
        if not self.state:
            return
        try:
            os.makedirs(os.path.dirname(self.save_path()), exist_ok=True)
            with open(self.save_path(), 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_state(self):
        if not self.has_save():
            return None
        try:
            with open(self.save_path(), 'r', encoding='utf-8') as f:
                return GameState.from_dict(json.load(f))
        except Exception:
            return None

    def clear_save(self):
        try:
            if self.has_save():
                os.remove(self.save_path())
        except Exception:
            pass

    # ---------- 页面跳转 ----------
    def choose_difficulty(self, key):
        self.state = GameState(key)
        self.save_state()
        self.sm.current = 'game'

    def continue_game(self):
        st = self.load_state()
        if st:
            self.state = st
            self.sm.current = 'game'
        else:
            self.notify('提示', '没有可继续的存档')

    def goto_menu(self):
        self.save_state()
        self.sm.current = 'menu'

    def replay(self):
        diff = self.state.difficulty if self.state else 'easy'
        self.state = GameState(diff)
        self.save_state()
        self.sm.current = 'game'

    def show_game_over(self, win, total):
        game = self.sm.get_screen('game')
        if game.game_ended:
            return
        game.game_ended = True
        self.clear_save()
        over = self.sm.get_screen('over')
        st = self.state
        if win:
            over.ids.result_emoji.text = '🏆'
            over.ids.result_title.text = '挑战成功！'
            over.ids.result_title.color = C_GOLD
        else:
            over.ids.result_emoji.text = '💥'
            over.ids.result_title.text = '破产出局'
            over.ids.result_title.color = C_RED
        over.ids.result_stats.text = (
            f"难度：{DIFFICULTIES[st.difficulty]['name']}\n"
            f"初始资金：{fmt(st.start_funds)} 元\n"
            f"最终总资产：{fmt(total)} 元\n"
            f"累计盈亏：{fmt(total - st.start_funds)} 元\n"
            f"完成交易：{st.trades} 笔"
        )
        self.sm.current = 'over'

    # ---------- 弹窗 ----------
    def notify(self, title, message):
        content = PopupBox(orientation='vertical', padding=dp(16), spacing=dp(12))
        tl = Label(text=title, bold=True, font_size=dp(18), color=C_GOLD,
                   halign='left', valign='middle', size_hint_y=None, height=dp(30))
        tl.bind(width=lambda *a: setattr(tl, 'text_size', (tl.width, None)))
        msg = Label(text=str(message), color=C_TEXT, font_size=dp(14),
                    halign='left', valign='top', size_hint_y=None)
        msg.bind(width=lambda *a: setattr(msg, 'text_size', (msg.width, None)))
        msg.bind(texture_size=lambda *a: setattr(msg, 'height', msg.texture_size[1] + dp(4)))
        btn = RButton(text='知道了', size_hint_y=None, height=dp(46),
                      bg=C_ACCENT, bg_down=C_ACCENT_D)
        content.add_widget(tl)
        content.add_widget(msg)
        content.add_widget(btn)
        popup = Popup(content=content, size_hint=(0.88, None), height=dp(260),
                      auto_dismiss=True)
        popup.background = ''
        popup.background_color = (0, 0, 0, 0)
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def show_popup_text(self, title, text):
        content = PopupBox(orientation='vertical', padding=dp(16), spacing=dp(10))
        tl = Label(text=title, bold=True, font_size=dp(18), color=C_GOLD,
                   halign='left', valign='middle', size_hint_y=None, height=dp(30))
        tl.bind(width=lambda *a: setattr(tl, 'text_size', (tl.width, None)))
        sc = ScrollLabel(text=text, size_hint=(1, 0.9))
        btn = RButton(text='关闭', size_hint_y=None, height=dp(46),
                      bg=C_ACCENT, bg_down=C_ACCENT_D)
        content.add_widget(tl)
        content.add_widget(sc)
        content.add_widget(btn)
        popup = Popup(content=content, size_hint=(0.9, 0.8), auto_dismiss=True)
        popup.background = ''
        popup.background_color = (0, 0, 0, 0)
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def show_rules(self):
        self.show_popup_text('交易规则', RULES_TEXT)

    def show_disclaimer(self):
        self.show_popup_text('免责声明', DISCLAIMER_TEXT)


if __name__ == '__main__':
    StockSimApp().run()
