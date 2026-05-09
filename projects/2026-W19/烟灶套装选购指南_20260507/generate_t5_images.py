#!/usr/bin/env python3
"""
T5 配图生成脚本 · 烟灶套装选购指南
Generate 6 professional infographic images for 今日头条 article.
Uses matplotlib (NOT Pillow/PIL) for data viz quality.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc, Polygon, Rectangle, Circle, Ellipse, Wedge
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import os

# ── Configuration ──────────────────────────────────────────────
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
DPI = 144  # High resolution

# Chinese font setup - try multiple options
FONT_CANDIDATES = [
    'PingFang HK', 'Heiti TC', 'STHeiti', 'Hiragino Sans GB',
    'Lantinghei SC', 'Hei', 'Songti SC', 'Apple LiGothic',
    'Kaiti SC', 'SimHei', 'Microsoft YaHei', 'Noto Sans CJK SC',
]
FONT_FAMILY = None
for f in FONT_CANDIDATES:
    try:
        from matplotlib.font_manager import FontProperties
        fp = FontProperties(family=f)
        FONT_FAMILY = f
        break
    except:
        continue
if FONT_FAMILY is None:
    FONT_FAMILY = 'sans-serif'

plt.rcParams['font.family'] = FONT_FAMILY
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 12

# Color palette (professional tech aesthetic)
C_BG_DARK = '#1a1a2e'
C_BG_MID = '#16213e'
C_GOLD = '#d4a853'
C_WHITE = '#ffffff'
C_GREY_TEXT = '#c0c0c0'
C_GREY_DARK = '#555555'
C_BLUE_BRAND = '#2979ff'       # 美的 blue
C_RED_BRAND = '#c62828'        # 方太 red
C_ORANGE_BRAND = '#ef6c00'     # 老板 orange
C_SKY_BRAND = '#0288d1'        # 海尔 sky blue
C_GREEN = '#2e7d32'
C_RED = '#c62828'
C_YELLOW = '#f9a825'
C_PURPLE = '#6a1b9a'

print(f"Using font: {FONT_FAMILY}")
print(f"Output directory: {OUTPUT_DIR}")

# ── Helper functions ───────────────────────────────────────────

def fig_to_png(fig, filename):
    """Save figure as PNG with proper settings."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(filepath, dpi=DPI, bbox_inches='tight', facecolor=fig.get_facecolor(),
                edgecolor='none', pad_inches=0.3)
    plt.close(fig)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"  -> Saved: {filename} ({size_kb:.0f} KB)")

def add_text_box(ax, x, y, w, h, text, color='white', fontsize=12, fontweight='bold',
                 bg_color=None, ha='center', va='center', border_color=None, corner_radius=0.02):
    """Add a text box with optional background."""
    kwargs = dict(facecolor=bg_color, alpha=1, transform=ax.transAxes)
    if border_color:
        kwargs['edgecolor'] = border_color
        kwargs['linewidth'] = 1.5
    if corner_radius > 0:
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle=f"round,pad=0,rounding_size={corner_radius}",
                             **kwargs)
    else:
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                             boxstyle="square,pad=0", **kwargs)
    ax.add_patch(box)
    ax.text(x, y, text, transform=ax.transAxes, fontsize=fontsize, fontweight=fontweight,
            color=color, ha=ha, va=va, zorder=5)

def add_simple_text(ax, x, y, text, fontsize=14, fontweight='normal', color='white',
                     ha='center', va='center', alpha=1):
    """Add text without background box."""
    ax.text(x, y, text, transform=ax.transAxes, fontsize=fontsize, fontweight=fontweight,
            color=color, ha=ha, va=va, alpha=alpha)

def divider_line(ax, x, y, width, color='#555555', lw=1):
    """Add a horizontal divider line."""
    ax.plot([x, x + width], [y, y], color=color, linewidth=lw, transform=ax.transAxes, clip_on=False)


# ═══════════════════════════════════════════════════════════════
# IMAGE 1: COVER - 封面图 (16:9)
# ═══════════════════════════════════════════════════════════════

def generate_cover():
    """Generate the main cover infographic."""
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Background gradient (simulated with rectangles)
    n_strips = 200
    for i in range(n_strips):
        ratio = i / n_strips
        r = int(26 * (1 - ratio) + 22 * ratio)
        g = int(26 * (1 - ratio) + 33 * ratio)
        b = int(46 * (1 - ratio) + 62 * ratio)
        color = f'#{r:02x}{g:02x}{b:02x}'
        ax.fill_between([0, 16], i*9/n_strips, (i+1)*9/n_strips, color=color, alpha=1)

    # Decorative geometric elements
    # Subtle circle in top-right
    circle = Circle((14, 8), 2.5, fill=False, edgecolor=C_GOLD, alpha=0.15, linewidth=1)
    ax.add_patch(circle)
    circle2 = Circle((14, 8), 1.8, fill=False, edgecolor=C_GOLD, alpha=0.1, linewidth=0.5)
    ax.add_patch(circle2)

    # Subtle lines
    for i in range(5):
        y = 2 + i * 1.5
        ax.plot([0.5, 2.5], [y, y], color=C_GOLD, alpha=0.08, linewidth=1)

    # Tech pattern - abstract range hood icon
    # Simplified duct/vent lines
    for offset in [0, 0.8, 1.6]:
        ax.plot([13.5 + offset, 14.0 + offset], [1.5, 3.5], color=C_GOLD, alpha=0.15, linewidth=1.5)
        ax.plot([13.5 + offset, 14.0 + offset], [3.5, 1.5], color=C_GOLD, alpha=0.08, linewidth=1)

    # MAIN TITLE
    add_simple_text(ax, 0.5, 0.78, '2026年618', fontsize=28, fontweight='normal',
                     color=C_GOLD, alpha=0.95)
    add_simple_text(ax, 0.5, 0.68, '烟灶套装怎么选？', fontsize=46, fontweight='bold',
                     color=C_WHITE)

    # Subtitle
    add_simple_text(ax, 0.5, 0.55, '美的 · 方太 · 老板 · 海尔  全价位横评', fontsize=20,
                     fontweight='normal', color=C_GREY_TEXT)

    # Key info row
    info_y = 0.42
    # Three boxes
    for i, (label, value) in enumerate([
        ('价位覆盖', '1500 - 4500元'),
        ('对比品牌', '美的 / 方太 / 老板 / 海尔'),
        ('实测套装', '30+ 款精选'),
    ]):
        x = 0.18 + i * 0.32
        # Small gold left bar
        ax.plot([x - 0.12, x - 0.12], [info_y - 0.04, info_y + 0.04],
                color=C_GOLD, linewidth=2, transform=ax.transAxes)
        add_simple_text(ax, x, info_y + 0.03, label, fontsize=11, color=C_GOLD, alpha=0.8)
        add_simple_text(ax, x, info_y - 0.03, value, fontsize=13, fontweight='bold', color=C_WHITE)

    # Bottom promise
    divider_line(ax, 0.2, 0.30, 0.6, color=C_GOLD, lw=0.5)
    add_simple_text(ax, 0.5, 0.24, '拆了 30+ 款套装，每个价位只推荐 2 款', fontsize=16,
                     fontweight='normal', color=C_WHITE, alpha=0.85)
    divider_line(ax, 0.2, 0.18, 0.6, color=C_GOLD, lw=0.5)

    # Bottom meta
    add_simple_text(ax, 0.5, 0.12, '2026年5月  |  数据来源：京东实时数据  |  含国家以旧换新补贴解读', fontsize=10,
                     color=C_GREY_TEXT, alpha=0.6)

    # Brand indicators at very bottom
    brands = ['Midea 美的', 'FOTILE 方太', 'ROBAM 老板', 'Haier 海尔']
    colors_b = [C_BLUE_BRAND, C_RED_BRAND, C_ORANGE_BRAND, C_SKY_BRAND]
    for i, (b, c) in enumerate(zip(brands, colors_b)):
        x = 0.2 + i * 0.2
        ax.plot(x, 0.06, 'o', color=c, markersize=5, transform=ax.transAxes)
        add_simple_text(ax, x + 0.02, 0.06, b, fontsize=7, color=c, ha='left', alpha=0.7)

    fig_to_png(fig, 'T5_封面图.png')


# ═══════════════════════════════════════════════════════════════
# IMAGE 2: BRAND × PRICE TIER COMPARISON (16:9)
# ═══════════════════════════════════════════════════════════════

def generate_brand_price_comparison():
    """Four brands × four price tiers matrix comparison chart."""
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # White background
    ax.set_facecolor('white')

    # Title
    add_simple_text(ax, 0.5, 0.95, '四大品牌 × 四大价位  烟灶套装横评', fontsize=24,
                     fontweight='bold', color='#1a1a2e')

    # Subtitle
    add_simple_text(ax, 0.5, 0.90, '数据来源：京东实时数据  |  采集时间：2026-05-07  |  价格为补贴后到手价', fontsize=9,
                     color='#888888')

    # Brand headers
    brands = ['美的', '方太', '老板', '海尔（统帅）']
    brand_colors = [C_BLUE_BRAND, C_RED_BRAND, C_ORANGE_BRAND, C_SKY_BRAND]
    price_tiers = ['1500元档', '2500元档', '3500元档', '4500元档']

    # Grid layout
    grid_left = 0.10
    grid_right = 0.94
    grid_top = 0.86
    grid_bottom = 0.10

    col_w = (grid_right - grid_left) / 4
    row_h = (grid_top - grid_bottom) / 4

    # Column headers (brands)
    for i, (brand, color) in enumerate(zip(brands, brand_colors)):
        x = grid_left + (i + 0.5) * col_w
        y = grid_top + 0.01
        add_simple_text(ax, x, y + 0.02, brand, fontsize=12, fontweight='bold', color=color)

    # Row headers (price tiers)
    for i, tier in enumerate(price_tiers):
        y = grid_top - (i + 0.5) * row_h
        add_simple_text(ax, grid_left - 0.02, y, tier, fontsize=10, fontweight='bold',
                         color='#333333', ha='right')

    # Data matrix
    rows_data = [
        # 1500元档
        [
            {'model': '—', 'spec': '此价位为单品非套装', 'price': '', 'highlight': False, 'note': ''},
            {'model': '—', 'spec': '此价位为单品非套装', 'price': '', 'highlight': False, 'note': ''},
            {'model': '—', 'spec': '此价位为单品非套装', 'price': '', 'highlight': False, 'note': ''},
            {'model': '统帅F28套装', 'spec': '28m³ 顶侧双吸', 'price': '¥1,598', 'highlight': True, 'note': '入门首选'},
        ],
        # 2500元档
        [
            {'model': 'DP55套装', 'spec': '23m³ 自动清洗', 'price': '¥2,048-2,987', 'highlight': False, 'note': ''},
            {'model': 'EMC2A+TX22', 'spec': '22m³ 挥手智控', 'price': '¥2,787', 'highlight': False, 'note': '品牌标杆'},
            {'model': '60A0S+F30', 'spec': '24m³ 一级能效', 'price': '¥2,331', 'highlight': True, 'note': '参数领先'},
            {'model': '—', 'spec': '此价位无主力套装', 'price': '', 'highlight': False, 'note': ''},
        ],
        # 3500元档
        [
            {'model': 'AK7 PRO', 'spec': '28m³ 蒸汽洗', 'price': '¥3,528', 'highlight': True, 'note': '10万+销量'},
            {'model': 'EMD20T', 'spec': '22m³ 直流变频', 'price': '¥3,168', 'highlight': False, 'note': ''},
            {'model': '小黑翼D1P', 'spec': '27m³ 顶侧双吸', 'price': '¥3,513', 'highlight': False, 'note': ''},
            {'model': 'C61Max+H70D', 'spec': '30m³ 热熔洗', 'price': '¥2,983', 'highlight': True, 'note': '折扣榜第1'},
        ],
        # 4500元档
        [
            {'model': 'AK9PRO套装', 'spec': '30m³ 变频', 'price': '¥3,198', 'highlight': True, 'note': '蒸汽洗'},
            {'model': 'HE1-G套装', 'spec': '29m³ 1450Pa', 'price': '¥4,408', 'highlight': False, 'note': '静压天花板'},
            {'model': '—', 'spec': '小黑翼D1P已覆盖3500档', 'price': '', 'highlight': False, 'note': ''},
            {'model': '—', 'spec': 'C61Max已覆盖3000档', 'price': '', 'highlight': False, 'note': ''},
        ],
    ]

    for ri, row in enumerate(rows_data):
        for ci, cell in enumerate(row):
            x_center = grid_left + (ci + 0.5) * col_w
            y_center = grid_top - (ri + 0.5) * row_h
            cell_w = col_w * 0.78
            cell_h = row_h * 0.75

            # Cell background
            if cell['highlight']:
                bg_color = '#f5f9ff'
                border_color = brand_colors[ci]
            else:
                bg_color = '#fafafa'
                border_color = '#e0e0e0'

            if cell['model'] != '—':
                cell_rect = FancyBboxPatch((x_center - cell_w/2, y_center - cell_h/2),
                                            cell_w, cell_h,
                                            boxstyle=f"round,pad=0,rounding_size=0.015",
                                            facecolor=bg_color, edgecolor=border_color,
                                            linewidth=1.5 if cell['highlight'] else 0.8)
                ax.add_patch(cell_rect)

                # Model name
                add_simple_text(ax, x_center, y_center + 0.025, cell['model'], fontsize=9,
                                 fontweight='bold', color='#1a1a2e')

                # Spec
                add_simple_text(ax, x_center, y_center - 0.01, cell['spec'], fontsize=7,
                                 color='#666666')

                # Price
                if cell['price']:
                    add_simple_text(ax, x_center + cell_w*0.28, y_center + 0.025,
                                     cell['price'], fontsize=8, fontweight='bold',
                                     color=brand_colors[ci], ha='right')

                # Highlight note
                if cell['note'] and cell['highlight']:
                    note_y = y_center - cell_h*0.35
                    note_bg = brand_colors[ci]
                    note_box = FancyBboxPatch((x_center - 0.08, note_y - 0.015),
                                               0.16, 0.03,
                                               boxstyle="round,pad=0,rounding_size=0.01",
                                               facecolor=note_bg, alpha=0.15)
                    ax.add_patch(note_box)
                    add_simple_text(ax, x_center, note_y, cell['note'], fontsize=6.5,
                                     color=brand_colors[ci], fontweight='bold')

    # Bottom disclaimer
    add_simple_text(ax, 0.5, 0.04, '注：灰色单元格为该品牌在该价位无主力套装产品  |  "—" 表示该品牌跳过此价位', fontsize=7, color='#aaaaaa')

    fig_to_png(fig, 'T5_四大品牌价位横评对比图.png')


# ═══════════════════════════════════════════════════════════════
# IMAGE 3: CORE PARAMETERS SELECTION GUIDE (16:9)
# ═══════════════════════════════════════════════════════════════

def generate_params_guide():
    """5 core parameters selection guide with card layout."""
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor('white')

    # Title
    add_simple_text(ax, 0.5, 0.95, '烟灶套装选购  5个必懂核心参数', fontsize=22,
                     fontweight='bold', color='#1a1a2e')
    add_simple_text(ax, 0.5, 0.89, '看懂这5个参数，谁也忽悠不了你', fontsize=11,
                     color='#888888')

    # Parameters data
    params = [
        {
            'name': '风量',
            'unit': 'm³/min',
            'icon': '💨',
            'color': '#2979ff',
            'desc': '每分钟能吸走多少立方米的油烟',
            'recommend': '日常22-24m³  爆炒28m³+',
            'trap': '标称风量≠实际吸力，看静压更靠谱',
        },
        {
            'name': '最大静压',
            'unit': 'Pa',
            'icon': '📊',
            'color': '#ef6c00',
            'desc': '对抗公共烟道排烟阻力的能力',
            'recommend': '高层住宅800Pa+  低层400Pa',
            'trap': '不带"最大"二字的静压值偏低30%+',
        },
        {
            'name': '火力',
            'unit': 'kW',
            'icon': '🔥',
            'color': '#c62828',
            'desc': '燃气灶的最大加热功率',
            'recommend': '中式爆炒5.0kW+  普通4.5kW',
            'trap': '火力大+热效率低=费气不旺火',
        },
        {
            'name': '热效率',
            'unit': '%',
            'icon': '⚡',
            'color': '#2e7d32',
            'desc': '燃气转化为有效热量的比例',
            'recommend': '新国标一级≥70%（硬门槛）',
            'trap': '＜63% = 旧国标库存机，无国补',
        },
        {
            'name': '自清洁',
            'unit': '技术',
            'icon': '🧹',
            'color': '#6a1b9c',
            'desc': '烟机内部油污自动清洗技术',
            'recommend': '蒸汽洗＞热熔洗＞免拆洗涂层',
            'trap': '免拆洗 ≠ 不用洗，只是延长间隔',
        },
    ]

    # 5-column card layout
    n = len(params)
    card_w = 0.145
    card_h = 0.60
    start_y = 0.78
    spacing = 0.17

    for i, p in enumerate(params):
        x = 0.115 + i * spacing
        y_top = start_y

        # Card background
        card = FancyBboxPatch((x - card_w/2, y_top - card_h), card_w, card_h,
                              boxstyle=f"round,pad=0,rounding_size=0.02",
                              facecolor='white', edgecolor='#e0e0e0', linewidth=1.2)
        ax.add_patch(card)

        # Top color bar
        top_bar = Rectangle((x - card_w/2, y_top - 0.04), card_w, 0.04,
                            facecolor=p['color'], alpha=0.9)
        ax.add_patch(top_bar)

        # Parameter name (large)
        add_simple_text(ax, x, y_top - 0.12, p['name'], fontsize=20,
                         fontweight='bold', color=p['color'])

        # Unit
        add_simple_text(ax, x, y_top - 0.18, p['unit'], fontsize=10,
                         color='#999999')

        # Divider
        divider_y = y_top - 0.23
        ax.plot([x - card_w*0.35, x + card_w*0.35], [divider_y, divider_y],
                color=p['color'], alpha=0.2, linewidth=1)

        # Description
        add_simple_text(ax, x, y_top - 0.30, p['desc'], fontsize=8.5,
                         color='#555555')

        # Recommend section
        rec_label = add_simple_text(ax, x, y_top - 0.40, '推荐', fontsize=8,
                                     fontweight='bold', color=p['color'])
        # Green box for recommendation
        rec_bg = FancyBboxPatch((x - card_w*0.38, y_top - 0.50 - 0.02),
                                card_w*0.76, 0.12,
                                boxstyle="round,pad=0,rounding_size=0.01",
                                facecolor='#e8f5e9', alpha=0.8)
        ax.add_patch(rec_bg)
        add_simple_text(ax, x, y_top - 0.45, p['recommend'], fontsize=7.5,
                         fontweight='bold', color='#2e7d32')

        # Trap section
        trap_bg = FancyBboxPatch((x - card_w*0.38, y_top - 0.63 - 0.02),
                                 card_w*0.76, 0.10,
                                 boxstyle="round,pad=0,rounding_size=0.01",
                                 facecolor='#ffebee', alpha=0.8)
        ax.add_patch(trap_bg)
        add_simple_text(ax, x, y_top - 0.56, '注意', fontsize=7,
                         fontweight='bold', color='#c62828')
        add_simple_text(ax, x, y_top - 0.60, p['trap'], fontsize=7,
                         color='#c62828')

    # Bottom mnemonic
    mnemonic = '口诀：风量看爆炒  |  静压看楼层  |  火力配效率  |  能效看国标  |  清洁选蒸汽'
    mnemonic_bg = FancyBboxPatch((0.08, 0.03), 0.84, 0.06,
                                  boxstyle="round,pad=0,rounding_size=0.015",
                                  facecolor='#fff3e0', edgecolor=C_GOLD, linewidth=1)
    ax.add_patch(mnemonic_bg)
    add_simple_text(ax, 0.5, 0.06, mnemonic, fontsize=9, fontweight='bold', color='#1a1a2e')

    fig_to_png(fig, 'T5_烟灶核心参数选购指南.png')


# ═══════════════════════════════════════════════════════════════
# IMAGE 4: INTEGRATED vs TRADITIONAL DECISION (16:9)
# ═══════════════════════════════════════════════════════════════

def generate_integrated_vs_traditional():
    """Integrated stove vs traditional range hood 8-dimension comparison."""
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor('white')

    # Title
    add_simple_text(ax, 0.5, 0.95, '集成灶 vs 传统烟灶套装  该怎么选？', fontsize=22,
                     fontweight='bold', color='#1a1a2e')
    add_simple_text(ax, 0.5, 0.89, '8 个维度全面对比，根据你家的情况做决定', fontsize=11, color='#888888')

    # Two side headers
    left_x = 0.28
    right_x = 0.72
    header_y = 0.84

    # Left header (集成灶)
    left_header = FancyBboxPatch((0.06, header_y - 0.02), 0.44, 0.05,
                                  boxstyle="round,pad=0,rounding_size=0.015",
                                  facecolor='#fff3e0', edgecolor=C_ORANGE_BRAND, linewidth=1.5)
    ax.add_patch(left_header)
    add_simple_text(ax, left_x, header_y + 0.005, '集成灶', fontsize=14, fontweight='bold',
                     color=C_ORANGE_BRAND)
    add_simple_text(ax, left_x, header_y - 0.025, '新装修 · 小厨房 · 预算5000-12000', fontsize=7.5,
                     color='#999999')

    # Right header (传统烟灶)
    right_header = FancyBboxPatch((0.50, header_y - 0.02), 0.44, 0.05,
                                   boxstyle="round,pad=0,rounding_size=0.015",
                                   facecolor='#e3f2fd', edgecolor=C_BLUE_BRAND, linewidth=1.5)
    ax.add_patch(right_header)
    add_simple_text(ax, right_x, header_y + 0.005, '传统烟灶套装', fontsize=14, fontweight='bold',
                     color=C_BLUE_BRAND)
    add_simple_text(ax, right_x, header_y - 0.025, '老房换装 · 预算1500-5000 · 大厨房', fontsize=7.5,
                     color='#999999')

    # VS icon in center
    vs_bg = Circle((0.5, header_y + 0.005), 0.025, facecolor='#ff5252', alpha=0.9, zorder=10)
    ax.add_patch(vs_bg)
    add_simple_text(ax, 0.5, header_y + 0.005, 'VS', fontsize=8, fontweight='bold',
                     color='white', ha='center')

    # 8 comparison dimensions
    dimensions = [
        ('空间利用', '✅ 释放吊柜\n❌ 切割地台连贯性', '⚠️ 占用吊柜空间\n✅ 地柜台面完整一体'),
        ('吸烟效果', '✅ 低空近吸15-25cm\n油烟不过脸', '✅ 顶侧双吸+30m³\n逼近集成灶效果'),
        ('功能集成', '✅ 烟机+灶+蒸烤箱\n一机多用', '⚠️ 仅烟机+灶具\n功能独立但灵活'),
        ('价格区间', '¥5,000-12,000+', '¥1,500-5,000'),
        ('安装难度', '❌ 需改烟道+定制橱柜\n工程量大', '✅ 即装即用 不改烟道\n几小时完成'),
        ('维修成本', '❌ 一体化设计\n一个坏可能整机修', '✅ 分体独立 哪个坏换哪个'),
        ('清洁维护', '⚠️ 部分带自清洁', '✅ 蒸汽洗/热熔洗/免拆洗\n多种技术可选'),
        ('适合场景', '毛坯新房 · 开放厨房\n厨房＜5㎡ · 蒸烤高频', '老房换装 · 预算可控\n大厨房 · 追求灵活'),
    ]

    start_y = 0.77
    row_h = 0.072

    for i, (dim, left_val, right_val) in enumerate(dimensions):
        y = start_y - i * row_h

        # Row background (alternating)
        if i % 2 == 0:
            row_bg = Rectangle((0.05, y - row_h/2), 0.90, row_h,
                              facecolor='#fafafa', alpha=1, zorder=-1)
            ax.add_patch(row_bg)

        # Dimension name (center label)
        dim_bg = FancyBboxPatch((0.41, y - 0.02), 0.18, 0.04,
                                 boxstyle="round,pad=0,rounding_size=0.01",
                                 facecolor='#37474f', alpha=0.9)
        ax.add_patch(dim_bg)
        add_simple_text(ax, 0.5, y, dim, fontsize=9, fontweight='bold', color='white')

        # Left value
        left_text = left_val.replace('✅', '●').replace('❌', '○').replace('⚠️', '◐')
        color = C_ORANGE_BRAND if '●' in left_text else ('#c62828' if '○' in left_text else '#555555')
        add_simple_text(ax, left_x, y, left_val, fontsize=8, color='#333333', ha='center',
                         fontweight='bold' if i <= 3 else 'normal')

        # Right value
        add_simple_text(ax, right_x, y, right_val, fontsize=8, color='#333333', ha='center',
                         fontweight='bold' if i >= 4 else 'normal')

    # Bottom decision box
    decision_y = start_y - len(dimensions) * row_h - 0.04
    decision_bg = FancyBboxPatch((0.08, 0.03), 0.84, 0.08,
                                  boxstyle="round,pad=0,rounding_size=0.015",
                                  facecolor='#1a1a2e', alpha=0.95)
    ax.add_patch(decision_bg)
    add_simple_text(ax, 0.28, 0.07, '新装修 + 小厨房  →  集成灶', fontsize=11,
                     fontweight='bold', color=C_ORANGE_BRAND)
    add_simple_text(ax, 0.50, 0.07, '|', fontsize=16, color='#555555')
    add_simple_text(ax, 0.72, 0.07, '老房换装 + 预算可控  →  传统烟灶套装', fontsize=11,
                     fontweight='bold', color=C_BLUE_BRAND)

    fig_to_png(fig, 'T5_集成灶vs传统烟灶决策图.png')


# ═══════════════════════════════════════════════════════════════
# IMAGE 5: SELF-CLEANING TECHNOLOGY COMPARISON (1:1)
# ═══════════════════════════════════════════════════════════════

def generate_self_cleaning_comparison():
    """Three self-cleaning technology routes comparison (1:1 square)."""
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_facecolor('white')

    # Title
    add_simple_text(ax, 0.5, 0.97, '蒸汽洗 vs 热熔洗 vs 免拆洗', fontsize=18,
                     fontweight='bold', color='#1a1a2e')
    add_simple_text(ax, 0.5, 0.93, '油烟机自清洁技术路线全面对比', fontsize=10, color='#888888')

    # Three technology routes
    routes = [
        {
            'name': '高温蒸汽洗',
            'brand': '代表品牌：美的',
            'analogy': '像洗碗机工作原理',
            'principle': '110℃高温蒸汽 + 高压水冲刷叶轮蜗壳',
            'effect': '洗净率 99.1%（美的官方数据）',
            'pros': ['清洁效果最强', '深度清洗内部油污', '零额外耗材成本'],
            'cons': ['需手动给水盒加水', '清洗过程中有蒸汽排出'],
            'cost_3yr': '0 元',
            'cost_label': '完全零成本',
            'color': '#1565c0',
            'icon': '🔵',
            'who': '重油爆炒家庭\n每年烹饪300次以上\n不想花钱请人洗',
        },
        {
            'name': '热熔自清洁',
            'brand': '代表品牌：海尔/华帝',
            'analogy': '像电吹风烘干原理',
            'principle': '70-80℃加热融化油脂 + 高速旋转离心甩出',
            'effect': '轻度油污有效，重油污需手动拆洗',
            'pros': ['零耗材无需加水', '操作简单一键启动', '日常维护省心'],
            'cons': ['顽固重油污效果有限', '长期使用仍需拆洗'],
            'cost_3yr': '约150-200 元',
            'cost_label': '第3年可能需拆洗1次',
            'color': '#ef6c00',
            'icon': '🟠',
            'who': '中等烹饪频率\n油污不算特别重\n喜欢简单操作',
        },
        {
            'name': '免拆洗涂层',
            'brand': '代表品牌：方太/老板',
            'analogy': '像不粘锅涂层原理',
            'principle': '纳米疏油材料涂覆叶轮表面，物理隔绝油污',
            'effect': '延缓油污积累，涂层2-3年后磨损',
            'pros': ['日常使用零额外操作', '配合大风量体验佳', '品牌质感好'],
            'cons': ['本质是延缓而非清洗', '油污还是会慢慢累积', '涂层长期会磨损'],
            'cost_3yr': '约450-600 元',
            'cost_label': '每年至少拆洗1次 = 2-3次/3年',
            'color': '#616161',
            'icon': '⚪',
            'who': '烹饪清淡\n注重品牌质感\n不介意定期花钱维护',
        },
    ]

    n = 3
    col_w = 0.26
    spacing = 0.30
    start_x = 0.10

    for i, route in enumerate(routes):
        x = start_x + i * spacing + col_w/2
        y_top = 0.88

        # Card
        card = FancyBboxPatch((x - col_w/2, 0.06), col_w, y_top - 0.06 - 0.05,
                               boxstyle=f"round,pad=0,rounding_size=0.02",
                               facecolor='white', edgecolor=route['color'], linewidth=1.5)
        ax.add_patch(card)

        # Top color header
        header_h = 0.10
        header = FancyBboxPatch((x - col_w/2 + 0.002, y_top - header_h), col_w - 0.004, header_h,
                                 boxstyle="round,pad=0,rounding_size=0.015",
                                 facecolor=route['color'], alpha=0.9)
        ax.add_patch(header)
        add_simple_text(ax, x, y_top - 0.04, route['name'], fontsize=13,
                         fontweight='bold', color='white')
        add_simple_text(ax, x, y_top - 0.07, route['brand'], fontsize=7,
                         color='white', alpha=0.85)

        cur_y = y_top - header_h - 0.04

        # Analogy
        add_simple_text(ax, x, cur_y, route['analogy'], fontsize=8.5,
                         fontweight='bold', color=route['color'])
        cur_y -= 0.035

        # Principle
        add_simple_text(ax, x, cur_y, route['principle'], fontsize=7.5, color='#555555')
        cur_y -= 0.04

        # Divider
        ax.plot([x - col_w*0.35, x + col_w*0.35], [cur_y, cur_y],
                color=route['color'], alpha=0.2, linewidth=0.8)
        cur_y -= 0.025

        # Effect
        effect_bg = FancyBboxPatch((x - col_w*0.40, cur_y - 0.025), col_w*0.80, 0.05,
                                    boxstyle="round,pad=0,rounding_size=0.01",
                                    facecolor='#e8eaf6', alpha=0.5)
        ax.add_patch(effect_bg)
        add_simple_text(ax, x, cur_y - 0.002, route['effect'], fontsize=7.5,
                         fontweight='bold', color=route['color'])
        cur_y -= 0.065

        # Pros section
        add_simple_text(ax, x - col_w*0.32, cur_y, '优点', fontsize=8, fontweight='bold',
                         color='#2e7d32', ha='left')
        cur_y -= 0.025
        for pro in route['pros']:
            add_simple_text(ax, x - col_w*0.30, cur_y, f'✅ {pro}', fontsize=7,
                             color='#333333', ha='left')
            cur_y -= 0.02

        cur_y -= 0.01

        # Cons section
        add_simple_text(ax, x - col_w*0.32, cur_y, '缺点', fontsize=8, fontweight='bold',
                         color='#c62828', ha='left')
        cur_y -= 0.025
        for con in route['cons']:
            add_simple_text(ax, x - col_w*0.30, cur_y, f'❌ {con}', fontsize=7,
                             color='#333333', ha='left')
            cur_y -= 0.02

        # Cost section (highlighted box)
        cost_y = 0.20
        cost_h = 0.09
        cost_bg = FancyBboxPatch((x - col_w*0.40, cost_y - cost_h/2), col_w*0.80, cost_h,
                                  boxstyle="round,pad=0,rounding_size=0.015",
                                  facecolor='#fff3e0', edgecolor=C_GOLD, linewidth=1)
        ax.add_patch(cost_bg)
        add_simple_text(ax, x, cost_y + 0.025, '三年使用成本', fontsize=7, color='#999999')
        add_simple_text(ax, x, cost_y + 0.005, route['cost_3yr'], fontsize=12,
                         fontweight='bold', color='#1a1a2e')
        add_simple_text(ax, x, cost_y - 0.018, route['cost_label'], fontsize=7,
                         color='#666666')

        # Who section
        add_simple_text(ax, x, 0.08, route['who'], fontsize=7, color='#777777')

    # Bottom conclusion
    conclusion_bg = FancyBboxPatch((0.08, 0.005), 0.84, 0.045,
                                    boxstyle="round,pad=0,rounding_size=0.015",
                                    facecolor='#1a1a2e', alpha=0.95)
    ax.add_patch(conclusion_bg)
    add_simple_text(ax, 0.5, 0.028, '经常爆炒 → 蒸汽洗  |  中度使用 → 热熔洗  |  清淡饮食+定期维护 → 免拆洗', fontsize=8.5,
                    fontweight='bold', color=C_GOLD)

    fig_to_png(fig, 'T5_自清洁技术路线对比图.png')


# ═══════════════════════════════════════════════════════════════
# IMAGE 6: PURCHASE DECISION FLOWCHART (16:9)
# ═══════════════════════════════════════════════════════════════

def generate_decision_flowchart():
    """Purchase decision flowchart from budget to final model."""
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')
    ax.set_facecolor('white')

    # Title
    add_simple_text(ax, 0.5, 0.97, '2026年618  烟灶套装选购决策地图', fontsize=22,
                     fontweight='bold', color='#1a1a2e')
    add_simple_text(ax, 0.5, 0.92, '三步锁定最适合你的烟灶套装', fontsize=11, color='#888888')

    # Step 1: Product Type Decision
    step1_y = 0.85
    step1_bg = FancyBboxPatch((0.05, step1_y - 0.06), 0.90, 0.10,
                               boxstyle="round,pad=0,rounding_size=0.015",
                               facecolor='#e8eaf6', edgecolor='#5c6bc0', linewidth=1.5)
    ax.add_patch(step1_bg)
    add_simple_text(ax, 0.08, step1_y + 0.02, '第一步', fontsize=8, fontweight='bold', color='#5c6bc0', ha='left')
    add_simple_text(ax, 0.08, step1_y - 0.02, '确定产品类型：你家是新装修还是老房换装？', fontsize=12,
                     fontweight='bold', color='#1a1a2e', ha='left')

    # Two branches
    # Branch 1: New renovation
    b1_x, b1_y = 0.25, step1_y - 0.12
    b1_box = FancyBboxPatch((b1_x - 0.18, b1_y - 0.03), 0.36, 0.06,
                             boxstyle="round,pad=0,rounding_size=0.012",
                             facecolor='#fff3e0', edgecolor=C_ORANGE_BRAND, linewidth=1.5)
    ax.add_patch(b1_box)
    add_simple_text(ax, b1_x, b1_y, '新装修 / 小厨房 / 预算5000+', fontsize=9,
                     fontweight='bold', color=C_ORANGE_BRAND)

    # Arrow to integrated stove recommendation
    add_simple_text(ax, 0.11, b1_y - 0.07, '⬇️ 推荐', fontsize=7, color='#999999')
    rec_b1 = FancyBboxPatch((0.04, b1_y - 0.12), 0.22, 0.05,
                              boxstyle="round,pad=0,rounding_size=0.01",
                              facecolor=C_ORANGE_BRAND, alpha=0.15, edgecolor=C_ORANGE_BRAND)
    ax.add_patch(rec_b1)
    add_simple_text(ax, 0.15, b1_y - 0.095, '集成灶', fontsize=10, fontweight='bold', color=C_ORANGE_BRAND)
    add_simple_text(ax, 0.15, b1_y - 0.125, '¥5,000 - 15,000', fontsize=7, color='#999999')

    # Branch 2: Old house renovation
    b2_x, b2_y = 0.72, step1_y - 0.12
    b2_box = FancyBboxPatch((b2_x - 0.20, b2_y - 0.03), 0.40, 0.06,
                             boxstyle="round,pad=0,rounding_size=0.012",
                             facecolor='#e3f2fd', edgecolor=C_BLUE_BRAND, linewidth=1.5)
    ax.add_patch(b2_box)
    add_simple_text(ax, b2_x, b2_y, '老房换装 / 预算1500-5000元', fontsize=9,
                     fontweight='bold', color=C_BLUE_BRAND)

    # Arrow down
    add_simple_text(ax, b2_x, b1_y - 0.07, '⬇️', fontsize=9, color=C_BLUE_BRAND)

    # Step 2: Budget Decision (5 budget tiers)
    step2_y = 0.65
    add_simple_text(ax, 0.5, step2_y + 0.03, '第二步：确定预算区间', fontsize=13, fontweight='bold',
                     color='#333333')

    budget_tiers = [
        ('1500-2000元', '统帅 F28套装', '¥1,598', '28m³ / 顶侧双吸', '预算紧张的首选', C_SKY_BRAND),
        ('2000-2500元', '老板60A0S+F30', '¥2,331', '24m³ / 一级能效', '主流品质之选', C_ORANGE_BRAND),
        ('2500-3000元', '方太EMC2A+TX22', '¥2,787', '22m³ / 挥手智控', '品牌服务标杆', C_RED_BRAND),
        ('3000-3500元', '海尔C61Max+H70D', '¥2,983', '30m³ / 智慧联动', '参数党的最爱', C_SKY_BRAND),
        ('3500-4500元', '美的AK7 PRO', '¥3,528', '28m³ / 蒸汽洗', '自清洁标杆', C_BLUE_BRAND),
    ]

    n_b = len(budget_tiers)
    b_width = 0.16
    b_start_x = 0.10
    b_spacing = 0.168

    for i, (tier, model, price, spec, tag, color) in enumerate(budget_tiers):
        bx = b_start_x + i * b_spacing + b_width/2

        # Budget tier card
        card = FancyBboxPatch((bx - b_width/2, step2_y - 0.22), b_width, 0.24,
                               boxstyle="round,pad=0,rounding_size=0.012",
                               facecolor='white', edgecolor=color, linewidth=1.2)
        ax.add_patch(card)

        # Budget label (top)
        tier_bg = FancyBboxPatch((bx - b_width/2 + 0.002, step2_y - 0.03), b_width - 0.004, 0.06,
                                  boxstyle="round,pad=0,rounding_size=0.01",
                                  facecolor=color, alpha=0.85)
        ax.add_patch(tier_bg)
        add_simple_text(ax, bx, step2_y, tier, fontsize=9, fontweight='bold', color='white')

        # Model name
        add_simple_text(ax, bx, step2_y - 0.07, model, fontsize=8, fontweight='bold', color='#1a1a2e')

        # Price
        add_simple_text(ax, bx, step2_y - 0.10, price, fontsize=9, fontweight='bold', color=color)

        # Spec
        add_simple_text(ax, bx, step2_y - 0.13, spec, fontsize=6.5, color='#666666')

        # Tag
        tag_bg = FancyBboxPatch((bx - 0.06, step2_y - 0.17), 0.12, 0.025,
                                 boxstyle="round,pad=0,rounding_size=0.008",
                                 facecolor='#e8f5e9', alpha=0.8)
        ax.add_patch(tag_bg)
        add_simple_text(ax, bx, step2_y - 0.157, tag, fontsize=6, color='#2e7d32')

    # Step 3: Special Needs
    step3_y = 0.33
    add_simple_text(ax, 0.5, step3_y + 0.02, '第三步：特殊需求微调（可选）', fontsize=12, fontweight='bold',
                     color='#333333')

    specials = [
        ('重油爆炒+不想手洗', '优先选蒸汽洗款', C_BLUE_BRAND, '美的AK7 PRO / AK9PRO'),
        ('高层住宅怕倒灌', '优先选变频+高静压款', C_SKY_BRAND, '方太HE1-G 1450Pa\n海尔C61Max 1200Pa'),
        ('老厨房不改橱柜', '优先选小尺寸顶侧双吸', C_ORANGE_BRAND, '老板小黑翼D1P\n海尔C61Max'),
    ]

    for i, (scenario, advice, color, models) in enumerate(specials):
        sx = 0.20 + i * 0.30
        sy = step3_y - 0.10

        # Card
        scard = FancyBboxPatch((sx - 0.13, sy - 0.09), 0.26, 0.18,
                                boxstyle="round,pad=0,rounding_size=0.015",
                                facecolor='white', edgecolor=color, linewidth=1.2)
        ax.add_patch(scard)

        # Scenario header
        add_simple_text(ax, sx, sy + 0.05, scenario, fontsize=8.5, fontweight='bold', color=color)
        add_simple_text(ax, sx, sy + 0.02, advice, fontsize=10, fontweight='bold', color='#1a1a2e')
        ax.plot([sx - 0.10, sx + 0.10], [sy, sy], color=color, alpha=0.2, linewidth=0.8)
        add_simple_text(ax, sx, sy - 0.06, models, fontsize=7.5, color='#555555')

    # Bottom note
    note_bg = FancyBboxPatch((0.12, 0.04), 0.76, 0.05,
                               boxstyle="round,pad=0,rounding_size=0.01",
                               facecolor='#f5f5f5', alpha=0.8)
    ax.add_patch(note_bg)
    add_simple_text(ax, 0.5, 0.065, '价格来源：京东2026-05-07实时数据  |  含国家以旧换新补贴  |  618期间价格可能波动10-20%', fontsize=7,
                     color='#999999')

    fig_to_png(fig, 'T5_选购决策流程图.png')


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 60)
    print("T5 配图生成 · 烟灶套装选购指南")
    print("=" * 60)

    print("\n[1/6] Generating cover image...")
    generate_cover()

    print("\n[2/6] Generating brand × price tier comparison...")
    generate_brand_price_comparison()

    print("\n[3/6] Generating core parameters guide...")
    generate_params_guide()

    print("\n[4/6] Generating integrated vs traditional decision chart...")
    generate_integrated_vs_traditional()

    print("\n[5/6] Generating self-cleaning technology comparison...")
    generate_self_cleaning_comparison()

    print("\n[6/6] Generating purchase decision flowchart...")
    generate_decision_flowchart()

    print("\n" + "=" * 60)
    print("All 6 images generated successfully!")
    print("=" * 60)

    # Verify outputs
    print("\nVerification:")
    import glob
    pngs = sorted(glob.glob(os.path.join(OUTPUT_DIR, 'T5_*.png')))
    for p in pngs:
        size_kb = os.path.getsize(p) / 1024
        print(f"  {os.path.basename(p):50s} {size_kb:6.0f} KB")
    print(f"\nTotal: {len(pngs)} PNG files (expected >= 5)")
