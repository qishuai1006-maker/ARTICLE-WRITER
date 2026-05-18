#!/usr/bin/env python3
"""
ContentFleet v6.5 · T3 文章质检脚本（lint_article.py）
=====================================================
用法:
  python3 Scripts/lint_article.py outputs/T3_头条.md [--fix] [--json]

功能:
  在 T3 提交 T4 审查前，自动扫描并拦截常见质量问题。
  v6.5 新增：7个AI高频词检测（来自khazix-writer禁区词）

  --fix   自动修复可自动替换的问题（绝对化用语），输出到同路径
  --json  以 JSON 格式输出结果（供 Hooks 集成使用）

退出码:
  0 = 全部通过
  1 = 存在 ERROR 级别问题（必须修复）
  2 = 仅有 WARNING 级别问题（建议修复）
"""

import os
import re
import sys
import json
from pathlib import Path

# ============================================================
# 绝对化用语扩展检测表（v6.0 · 从 T4 驳回案例提炼 + 广告法）
# ============================================================
ABSOLUTE_LANGUAGE_RULES = [
    # (原文模式, 替换建议, 来源)
    ("没有对手",       "属于第一梯队",       "洗衣机618横评"),
    ("基本没有对手",   "很有竞争力",         "扁桶热水器"),
    ("只此一款",       "目前市面上较少见的",  "扁桶热水器"),
    ("十有八九",       "很可能",             "空调内机滴水"),
    ("碾压",           "明显领先",           "电视横评"),
    ("吊打",           "明显领先",           "电视横评"),
    ("毫无疑问",       "",                   "AI味词库·删除即可"),
    ("不得不说",       "",                   "AI味词库·删除即可"),
    ("必须",           "建议",               "多个项目"),
    ("一定要",         "建议",               "多个项目"),
    ("最好的",         "表现突出的",         "广告法通用"),
    ("最强的",         "排名靠前的",         "广告法通用"),
    ("最佳",           "表现优秀",           "广告法通用"),
    ("最优",           "表现突出",           "广告法通用"),
    ("唯一",           "少有的",             "广告法通用"),
    ("独家",           "为数不多的",         "广告法通用"),
    ("第一",           "领先",               "广告法通用"),
    ("顶级",           "高端",               "广告法通用"),
    ("无敌",           "竞争力很强",         "广告法通用"),
    ("完美",           "表现出色",           "广告法通用"),
    ("秒杀一切",       "性价比很高",         "广告法通用"),
    ("必买",           "值得考虑",           "头条违禁词"),
    ("必入",           "值得关注",           "头条违禁词"),
    ("绝对",           "非常",               "广告法通用"),
    ("史上最",         "近年来表现突出的",   "广告法通用"),
]

# 允许出现在特定上下文中的豁免（防止误报）
EXEMPTIONS = [
    r"必须.{0,4}(遵守|执行|通过|满足|符合)",    # "必须遵守标准" 不算违规
    r"必须.{0,4}(装在|安装在|固定在|放在)",      # "必须装在承重墙" 物理要求
    r"一定要.{0,4}(注意|小心|确认|检查)",        # "一定要注意" 语境合理
    r"一定要.{0,4}(装在|安装在|固定在|打在)",     # "一定要装在承重墙" 物理安全要求
    r"一定要.{0,4}(选|买|看|问|确认|找)",        # "一定要看清楚" 选购建议
    r"第一(步|次|时间|梯队|印象|层|波|个|台|年|批|季度|阶段|款|名|天|周|轮|期|代|版)",
    r"第一[，,；;]",                              # "第一，新增了..." 列举用法
    r"唯一.{0,4}(标识|编号|ID|标准)",            # 技术术语
    r"绝对(红线|禁止|不可|值|温度|湿度|误差)",    # 规则描述 + 技术术语
    r"绝对.{0,2}(不[能会行])",                   # "绝对不能" 安全警告用语
]

# 抖音达人引述检测
DOUYIN_CITATION_PATTERNS = [
    r"抖音达人.{0,4}(说|表示|认为|提到|推荐|建议)",
    r"抖音上.{0,6}(达人|博主|大V|up主)",
    r"好几位达人",
    r"有位达人",
    r"某位达人",
    r"达人们?.{0,4}(都在说|都在推|一致认为|纷纷)",
]

# 催互动检测
ENGAGEMENT_BAIT_PATTERNS = [
    r"点赞",
    r"收藏",
    r"转发",
    r"双击",
    r"关注.{0,2}(我|一下)",
    r"评论区.{0,4}(留言|告诉|说说)",
]

# ============================================================
# 检查函数
# ============================================================

class LintResult:
    def __init__(self):
        self.errors = []    # 必须修复
        self.warnings = []  # 建议修复
        self.info = []      # 信息
        self.fixes = []     # 可自动修复项

    def add_error(self, line_num, msg, category=""):
        self.errors.append({"line": line_num, "msg": msg, "category": category})

    def add_warning(self, line_num, msg, category=""):
        self.warnings.append({"line": line_num, "msg": msg, "category": category})

    def add_info(self, msg):
        self.info.append(msg)

    def add_fix(self, line_num, original, replacement, reason):
        self.fixes.append({
            "line": line_num,
            "original": original,
            "replacement": replacement,
            "reason": reason
        })

    @property
    def passed(self):
        return len(self.errors) == 0

    def to_dict(self):
        return {
            "passed": self.passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "auto_fixable": len(self.fixes),
        }


def is_exempted(text, match_start, match_end):
    """检查匹配是否在豁免上下文中"""
    context = text[max(0, match_start - 10):min(len(text), match_end + 10)]
    for pattern in EXEMPTIONS:
        if re.search(pattern, context):
            return True
    return False


def check_absolute_language(lines, result):
    """扫描绝对化用语扩展检测表"""
    for i, line in enumerate(lines, 1):
        # 跳过元数据行和注释行
        if line.startswith("---") or line.startswith("#") or line.startswith(">"):
            continue
        for term, replacement, source in ABSOLUTE_LANGUAGE_RULES:
            for match in re.finditer(re.escape(term), line):
                if not is_exempted(line, match.start(), match.end()):
                    context = line.strip()[:80]
                    if replacement:
                        result.add_error(
                            i,
                            f'绝对化用语「{term}」→ 建议替换为「{replacement}」| 上下文: {context}',
                            "absolute_language"
                        )
                        result.add_fix(i, term, replacement, f"绝对化用语（来源: {source}）")
                    else:
                        result.add_error(
                            i,
                            f'AI味用语「{term}」→ 建议删除 | 上下文: {context}',
                            "ai_language"
                        )
                        result.add_fix(i, term, "", f"AI味用语·删除（来源: {source}）")


def check_exclamation_marks(lines, result):
    """检查感叹号（头条规范：零感叹号）"""
    import re
    total_excl = 0
    for i, line in enumerate(lines, 1):
        if line.startswith("#") or line.startswith(">") or line.startswith("---"):
            continue
        # 先移除 markdown 图片语法 ![alt](url)，避免误报
        cleaned = re.sub(r'!\[.*?\]\(.*?\)', '', line)
        count = cleaned.count("！") + cleaned.count("!")
        if count > 0:
            total_excl += count
            result.add_error(
                i,
                f'感叹号 ×{count} | {line.strip()[:60]}',
                "exclamation"
            )
    if total_excl == 0:
        result.add_info("✅ 零感叹号 — 符合头条规范")


def check_douyin_citations(lines, result):
    """检查正文是否引述抖音达人"""
    for i, line in enumerate(lines, 1):
        for pattern in DOUYIN_CITATION_PATTERNS:
            if re.search(pattern, line):
                result.add_error(
                    i,
                    f'正文引述抖音达人（禁止）| {line.strip()[:60]}',
                    "douyin_citation"
                )


def check_engagement_bait(lines, result):
    """检查催互动用语"""
    for i, line in enumerate(lines, 1):
        if line.startswith("#") or line.startswith(">"):
            continue
        for pattern in ENGAGEMENT_BAIT_PATTERNS:
            if re.search(pattern, line):
                result.add_warning(
                    i,
                    f'疑似催互动「{re.search(pattern, line).group()}」| {line.strip()[:60]}',
                    "engagement_bait"
                )


def check_word_count(content, result):
    """检查字数是否 ≥1500"""
    # 去掉 Markdown 标记和空行后计算
    clean = re.sub(r'[#*|\-`>\[\]()!]', '', content)
    clean = re.sub(r'\s+', '', clean)
    char_count = len(clean)

    if char_count < 1500:
        result.add_error(
            0,
            f'字数不足：当前 {char_count} 字，要求 ≥1500 字',
            "word_count"
        )
    else:
        result.add_info(f"✅ 字数 {char_count} 字 — 符合 ≥1500 要求")


def check_title(lines, result):
    """检查标题长度 ≤30 字（头条硬性限制）"""
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            title = line.lstrip("# ").strip()
            title_len = len(title)
            if title_len > 30:
                result.add_error(
                    lines.index(line) + 1,
                    f'标题超长：「{title}」共 {title_len} 字，头条限制 ≤30 字',
                    "title_length"
                )
            elif title_len > 25:
                result.add_warning(
                    lines.index(line) + 1,
                    f'标题接近上限：「{title}」共 {title_len} 字（上限30字）',
                    "title_length"
                )
            else:
                result.add_info(f"✅ 标题 {title_len} 字 — 符合 ≤30 字要求")
            break  # 只检查第一个 H1


def check_single_source_attribution(lines, result):
    """检查 SINGLE_SOURCE 数据是否标注来源"""
    # 在正文中搜索可能的裸写数据（没有来源标注的参数声明）
    # 这个检查比较保守，只检查最明显的模式
    naked_data_patterns = [
        r'洗净比\d+\.\d+',         # 洗净比1.28（无来源）
        r'能效比\d+\.\d+',         # 能效比4.5
        r'噪音值?\d+\.?\d*\s*dB',  # 噪音38dB
        r'耗电量?\d+\.?\d*\s*度',  # 耗电量1.2度
    ]
    source_markers = ["据", "来源", "标称", "实测", "官方", "京东", "产品库", "数据显示"]

    for i, line in enumerate(lines, 1):
        if line.startswith("#") or line.startswith(">") or line.startswith("|"):
            continue
        for pattern in naked_data_patterns:
            match = re.search(pattern, line)
            if match:
                # 检查前后 20 个字符是否有来源标注
                start = max(0, match.start() - 20)
                end = min(len(line), match.end() + 20)
                context = line[start:end]
                has_source = any(marker in context for marker in source_markers)
                if not has_source:
                    result.add_warning(
                        i,
                        f'疑似裸写参数「{match.group()}」— 如为 SINGLE_SOURCE 数据需标注来源 | {line.strip()[:60]}',
                        "single_source"
                    )


def check_ai_patterns(lines, result):
    """检查常见 AI 写作模式"""
    ai_patterns = [
        (r"首先.*其次.*最后", "机械三段式"),
        (r"因此[，,]", "建议替换为'所以'"),
        (r"但是[，,]", "建议替换为'不过'"),
        (r"综上所述", "AI味过重，建议删除"),
        (r"总而言之", "AI味过重，建议改为自然总结"),
        (r"值得注意的是", "AI味过重，建议直接说内容"),
        (r"在当今.*背景下", "AI味模板句式"),
        (r"随着.*的(发展|普及|进步)", "AI味开头模板"),
        # v6.5 新增：来自 khazix-writer 禁区词
        (r"不难发现", "AI标志词，建议直接说结论"),
        (r"不难看出", "AI标志词，建议直接说结论"),
        (r"本质上", "太学术，建议用'其实''说到底'"),
        (r"换句话说", "太书面，建议用'你想想看''也就是说'"),
        (r"不可否认", "AI套话，建议直接删掉"),
        (r"让我们来看看", "AI过渡句，建议删掉直接进入内容"),
        (r"接下来让我们", "AI过渡句，建议删掉直接进入内容"),
        (r"这意味着", "AI标志句式，建议换成更口语的表达"),
        (r"意味着什么[？?]", "AI标志句式，建议换成具体追问"),
        (r"众所周知", "AI空洞词，建议用'大家也都知道'或删掉"),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, reason in ai_patterns:
            if re.search(pattern, line):
                result.add_warning(
                    i,
                    f'AI写作模式「{reason}」| {line.strip()[:60]}',
                    "ai_pattern"
                )


def check_bad_opening(lines, result):
    """检查开头是否命中禁区模式（10-活人写手感.md 绝对禁区）"""
    # 找到正文开始的行（跳过标题、图片、注释、空行）
    content_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('![') and not stripped.startswith('<!--'):
            content_start = i
            break

    if content_start == 0:
        return

    # 检查正文前5行
    opening_lines = lines[content_start:content_start + 5]
    opening_text = "\n".join(opening_lines)

    bad_openings = [
        (r"^你知道吗", "「你知道吗」小学生作文开头"),
        (r"^很多人不知道", "「很多人不知道」自作聪明说教"),
        (r"^今天我要.{0,4}(给|跟|和你|分享|聊聊)", "「今天我要分享」课前发言"),
        (r"^随着.*的(发展|普及|进步|崛起)", "「随着…的发展」AI标准开头"),
        (r"^在当今.*的(背景|大环境|趋势)下", "「在当今…背景下」新闻联播体"),
        (r".*一直是消费者关注的话题", "「XX一直是关注话题」万能模板"),
        (r"^在购买.*时.{0,4}(很多人|大家|不少人).{0,4}(纠结|头疼|困惑)", "「购买XX时很多人纠结」电商导购AI标配"),
        (r"^近年来.*市场.{0,6}(发生了|出现了|经历了).{0,6}(巨大|显著|深刻)", "「近年来市场发生了巨大变化」通稿开头"),
    ]

    for pattern, reason in bad_openings:
        if re.search(pattern, opening_text):
            result.add_error(
                content_start + 1,
                f'开头命中禁区 → {reason} | 必须按10-Skill重新选择开场模式',
                "bad_opening"
            )
            break  # 只报一次


def check_bad_ending(lines, result):
    """检查结尾是否命中禁区模式（10-活人写手感.md 结尾绝对禁区）"""
    # 找到最后一个非空、非元数据的内容段落
    content_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('---') and not stripped.startswith('*') and not stripped.startswith('<!--'):
            content_lines.append((i + 1, stripped))

    if len(content_lines) < 3:
        return

    # 检查最后5个内容段落
    ending_lines = content_lines[-5:]
    ending_text = "\n".join([text for _, text in ending_lines])

    bad_endings = [
        (r"总而言之", "AI总结腔「总而言之」"),
        (r"综上所述", "AI总结腔「综上所述」"),
        (r"总的来说", "AI总结腔「总的来说」"),
        (r"希望这篇(文章|内容).{0,6}(对你有帮助|有所帮助)", "客服结束语「希望本文对你有帮助」"),
        (r"展望未来", "空洞展望「展望未来」"),
        (r"(充满|令人|让人).{0,2}(期待|期待)", "空洞展望「充满期待」"),
        (r"让我们.{0,4}(一起.{0,4}期待|共同期待)", "AI呼吁体「让我们一起期待」"),
        (r"赶紧行动起来", "催促互动「赶紧行动起来」"),
        (r"相信通过.{0,6}(本文|这篇).{0,4}(的)?(介绍|分析|解读)", "模板套话「相信通过本文的介绍」"),
    ]

    for pattern, reason in bad_endings:
        if re.search(pattern, ending_text):
            last_line_num = ending_lines[-1][0]
            result.add_warning(
                last_line_num,
                f'结尾命中禁区 → {reason} | 建议按10-Skill重新选择收尾模式',
                "bad_ending"
            )
            break  # 只报一次


# ============================================================
# 自动修复
# ============================================================

def apply_fixes(filepath, fixes):
    """应用自动修复"""
    content = Path(filepath).read_text("utf-8")
    fix_count = 0
    for fix in fixes:
        if fix["original"] and fix["original"] in content:
            if fix["replacement"]:
                content = content.replace(fix["original"], fix["replacement"], 1)
            else:
                # 删除型修复（去掉词语，保留前后文）
                content = content.replace(fix["original"], "", 1)
            fix_count += 1
    Path(filepath).write_text(content, "utf-8")
    return fix_count


# ============================================================
# 主流程
# ============================================================

class Colors:
    OK = "\033[92m"
    WARN = "\033[93m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def main():
    if len(sys.argv) < 2:
        print("用法: python3 Scripts/lint_article.py <T3文件路径> [--fix] [--json]")
        sys.exit(1)

    filepath = sys.argv[1]
    do_fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv

    if not Path(filepath).exists():
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    content = Path(filepath).read_text("utf-8")
    lines = content.split("\n")
    result = LintResult()

    # 执行所有检查
    check_title(lines, result)
    check_word_count(content, result)
    check_absolute_language(lines, result)
    check_exclamation_marks(lines, result)
    check_douyin_citations(lines, result)
    check_engagement_bait(lines, result)
    check_single_source_attribution(lines, result)
    check_ai_patterns(lines, result)
    check_bad_opening(lines, result)
    check_bad_ending(lines, result)

    # JSON 输出模式
    if as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        sys.exit(0 if result.passed else 1)

    # 终端输出
    filename = Path(filepath).name
    print(f"\n{Colors.BOLD}━━━ ContentFleet v6.5 T3 质检 · {filename} ━━━{Colors.RESET}\n")

    # 信息
    for info in result.info:
        print(f"  {info}")

    # 错误
    if result.errors:
        print(f"\n{Colors.FAIL}❌ ERROR × {len(result.errors)}（必须修复）{Colors.RESET}")
        for err in result.errors:
            line_info = f"L{err['line']}" if err['line'] > 0 else "全文"
            print(f"  {Colors.FAIL}[{line_info}]{Colors.RESET} {err['msg']}")

    # 警告
    if result.warnings:
        print(f"\n{Colors.WARN}⚠️  WARNING × {len(result.warnings)}（建议修复）{Colors.RESET}")
        for warn in result.warnings:
            line_info = f"L{warn['line']}" if warn['line'] > 0 else "全文"
            print(f"  {Colors.WARN}[{line_info}]{Colors.RESET} {warn['msg']}")

    # 自动修复
    if result.fixes and do_fix:
        print(f"\n{Colors.BOLD}🔧 自动修复...{Colors.RESET}")
        fix_count = apply_fixes(filepath, result.fixes)
        print(f"  已修复 {fix_count} 处，文件已更新: {filepath}")
    elif result.fixes and not do_fix:
        print(f"\n{Colors.DIM}💡 发现 {len(result.fixes)} 处可自动修复，运行 --fix 参数自动替换{Colors.RESET}")

    # 总结
    print(f"\n{Colors.BOLD}━━━ 总结 ━━━{Colors.RESET}")
    if result.passed:
        if result.warnings:
            print(f"  {Colors.WARN}⚠️  质检通过（有 {len(result.warnings)} 条警告）{Colors.RESET}")
            sys.exit(2)
        else:
            print(f"  {Colors.OK}✅ 质检全部通过{Colors.RESET}")
            sys.exit(0)
    else:
        print(f"  {Colors.FAIL}❌ 质检未通过 — {len(result.errors)} 个 ERROR 必须修复后才能提交 T4{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
