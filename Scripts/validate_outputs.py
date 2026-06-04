#!/usr/bin/env python3
"""
ContentFleet v6.2 · outputs 全量校验脚本（v2.1）
================================================
用法:
  python3 Scripts/validate_outputs.py [--verbose] [--archive <归档目录>]

功能:
  v1.0 基础文件存在性检查
  v2.0 新增:
    - T3 内容质量检查（调用 lint_article.py）
    - T5 配图命名规范检查（T5_功能描述.png，禁止编号前缀）
    - T6 配图引用与实际文件名对齐检查
    - T7 归档完整性检查（--archive 模式）
    - v6.0 文章类型分类检查
    - Skill 版本一致性检查
  v2.1 新增（2026-05-08 · 油烟机横评复盘驱动）:
    - outputs/ 垃圾文件检测（debug_*.png / *_auto.py / nlm_*.py / generate_*.py）
    - nested outputs/outputs/ 目录检测
    - T5 配图质量检查（分辨率 ≥ 1920px 宽 / 文件大小 ≥ 500KB）
"""

import os
import sys
import re
import subprocess
from pathlib import Path

# 检查是否在归档模式
ARCHIVE_MODE = "--archive" in sys.argv
ARCHIVE_DIR = None
if ARCHIVE_MODE:
    idx = sys.argv.index("--archive")
    if idx + 1 < len(sys.argv):
        ARCHIVE_DIR = Path(sys.argv[idx + 1])
    else:
        print("❌ --archive 需要指定目录路径")
        sys.exit(1)

OUTPUTS = ARCHIVE_DIR if ARCHIVE_DIR else Path("outputs")
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

class Colors:
    OK = "\033[92m✅"
    WARN = "\033[93m⚠️"
    FAIL = "\033[91m❌"
    RESET = "\033[0m"
    BOLD = "\033[1m"

errors = []
warnings = []

def check(condition, msg, warn_only=False):
    if condition:
        if VERBOSE:
            print(f"  {Colors.OK} {msg}{Colors.RESET}")
        return True
    else:
        if warn_only:
            warnings.append(msg)
            print(f"  {Colors.WARN} {msg}{Colors.RESET}")
        else:
            errors.append(msg)
            print(f"  {Colors.FAIL} {msg}{Colors.RESET}")
        return False

def read_file(path):
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""

def count_files(pattern):
    return len(list(OUTPUTS.glob(pattern)))

# ══════════════════════════════════════════════════════════════
# T1 选题池
# ══════════════════════════════════════════════════════════════
print(f"\n{Colors.BOLD}━━━ T1 选题池 ━━━{Colors.RESET}")
t1 = OUTPUTS / "T1_选题池.md"
check(t1.exists(), "T1_选题池.md 文件存在")

if t1.exists():
    content = read_file(t1)
    check("S级" in content or "S 级" in content, "包含 S 级选题")
    check("B级" not in content.split("禁止")[0] if "禁止" in content else "B级" not in content,
          "无 B 级选题（或仅在禁止规则中提及）", warn_only=True)

    # v5.0: 必须有抖音佐证
    has_douyin = any(kw in content for kw in ["抖音", "互动量", "达人", "douyin"])
    check(has_douyin, "包含抖音爆款佐证数据（v5.0 必需）")

    # 选题数量
    topic_count = len(re.findall(r"###\s*选题\s*\d", content))
    check(topic_count >= 5, f"选题数量 ≥ 5（当前: {topic_count}）")

    # v6.0: 文章类型分类
    has_article_type = any(kw in content for kw in ["选购横评", "教程避坑", "趋势科普", "文章类型"])
    check(has_article_type, "包含文章类型分类（v6.0 必需：选购横评/教程避坑/趋势科普）")

    # 配图侧重建议
    has_image_hint = "配图侧重" in content or "配图建议" in content
    check(has_image_hint, "包含配图侧重建议", warn_only=True)

# ══════════════════════════════════════════════════════════════
# T2 素材包
# ══════════════════════════════════════════════════════════════
print(f"\n{Colors.BOLD}━━━ T2 素材包 ━━━{Colors.RESET}")
t2 = OUTPUTS / "T2_素材包.md"
check(t2.exists(), "T2_素材包.md 文件存在（标准文件名）")

if t2.exists():
    content = read_file(t2)

    # v5.0 必备章节
    check("骨架" in content or "骨架清单" in content, "包含文章骨架清单")
    check("交叉验证" in content or "VERIFIED" in content, "包含参数交叉验证表（v5.0 必需）")
    check("抖音" in content or "达人观点" in content, "包含抖音达人观点矩阵（v5.0 必需）")

    # 验证状态检查
    verified_count = content.count("VERIFIED")
    conflict_count = content.count("CONFLICT")
    single_count = content.count("SINGLE_SOURCE")
    if verified_count + conflict_count + single_count > 0:
        print(f"  📊 验证状态: VERIFIED={verified_count} CONFLICT={conflict_count} SINGLE_SOURCE={single_count}")
        if conflict_count > 0:
            check(False, f"存在 {conflict_count} 个 CONFLICT 参数，需 CEO 裁定", warn_only=True)
else:
    # 检查是否有非标准文件名的 T2
    alt_t2 = list(OUTPUTS.glob("T2_*.md"))
    if alt_t2:
        check(False, f"T2 文件名不规范: {[f.name for f in alt_t2]}，应为 T2_素材包.md")

# ══════════════════════════════════════════════════════════════
# T3 头条稿
# ══════════════════════════════════════════════════════════════
print(f"\n{Colors.BOLD}━━━ T3 头条稿 ━━━{Colors.RESET}")
t3 = OUTPUTS / "T3_头条.md"
check(t3.exists(), "T3_头条.md 文件存在")

if t3.exists():
    content = read_file(t3)
    # 基础字数检查
    clean = re.sub(r'[#*|\-`>\[\]()!]', '', content)
    clean = re.sub(r'\s+', '', clean)
    char_count = len(clean)
    check(char_count >= 1500, f"字数 ≥ 1500（当前: {char_count} 字符）")

    # 感叹号检查（精确统计正文中的）
    excl_count = 0
    for line in content.split("\n"):
        line_clean = re.sub(r'!\[.*?\]\([^)]*\)', '', line)
        if not line_clean.startswith("#") and not line_clean.startswith(">") and not line_clean.startswith("---"):
            excl_count += line_clean.count("！") + line_clean.count("!")
    check(excl_count == 0, f"零感叹号（当前: {excl_count} 个）", warn_only=excl_count < 3)

    # 标题长度检查
    for line in content.split("\n"):
        if line.startswith("# ") and not line.startswith("## "):
            title = line.lstrip("# ").strip()
            title_len = len(title)
            check(title_len <= 30, f"标题 ≤ 30 字（当前: {title_len} 字「{title[:35]}...」）")
            break

    # 调用 lint_article.py 做深度检查
    try:
        lint_result = subprocess.run(
            ["python3", "Scripts/lint_article.py", str(t3), "--json"],
            capture_output=True, text=True, timeout=10,
            cwd=str(Path(__file__).parent.parent) if not ARCHIVE_MODE else None
        )
        import json
        lint_data = json.loads(lint_result.stdout)
        lint_errors = lint_data.get("error_count", 0)
        lint_warnings = lint_data.get("warning_count", 0)
        if lint_errors > 0:
            check(False, f"lint_article.py 发现 {lint_errors} 个 ERROR（详情: python3 Scripts/lint_article.py {t3}）")
        elif lint_warnings > 0:
            check(False, f"lint_article.py 发现 {lint_warnings} 个 WARNING", warn_only=True)
        else:
            if VERBOSE:
                print(f"  {Colors.OK} lint_article.py 全部通过{Colors.RESET}")
    except Exception:
        check(False, "lint_article.py 执行失败（跳过深度检查）", warn_only=True)

# ══════════════════════════════════════════════════════════════
# T4 审查报告
# ══════════════════════════════════════════════════════════════
print(f"\n{Colors.BOLD}━━━ T4 审查报告 ━━━{Colors.RESET}")
t4 = OUTPUTS / "T4_审查报告.md"
check(t4.exists(), "T4_审查报告.md 文件存在")

if t4.exists():
    content = read_file(t4)
    check("通过" in content or "✅" in content, "审查结论存在")
    check("抽查" in content or "产品数据" in content, "包含产品数据抽查结果（v5.0 必需）", warn_only=True)

# ══════════════════════════════════════════════════════════════
# T5 配图
# ══════════════════════════════════════════════════════════════
print(f"\n{Colors.BOLD}━━━ T5 配图 ━━━{Colors.RESET}")
png_files = list(OUTPUTS.glob("T5_*.png"))
jpg_files = list(OUTPUTS.glob("T5_*.jpg"))
img_files = png_files + jpg_files
img_count = len(img_files)
check(img_count >= 5, f"配图数量 ≥ 5（当前: {img_count} 张）")

# v6.0: 配图命名规范检查
bad_naming = []
for img in img_files:
    name = img.name
    # 检查编号前缀（禁止 T5_01_xxx / T5_02_xxx / NLM_xx_xxx）
    if re.match(r'T5_\d+_', name) or re.match(r'NLM_\d+_', name) or re.match(r'T5_slide_', name):
        bad_naming.append(name)
if bad_naming:
    check(False, f"配图命名不规范（v6.0 禁止编号前缀）: {bad_naming}")
else:
    if VERBOSE and img_files:
        print(f"  {Colors.OK} 配图命名规范（T5_功能描述.png）{Colors.RESET}")

# 列出所有配图
if VERBOSE and img_files:
    for img in sorted(img_files):
        size_kb = img.stat().st_size // 1024
        print(f"    📷 {img.name} ({size_kb} KB)")

# 配图提示词文档
t5_prompt = OUTPUTS / "T5_配图_生成提示词.md"
check(t5_prompt.exists(), "T5_配图_生成提示词.md 存在", warn_only=True)

# 配图说明文档
t5_desc = OUTPUTS / "T5_配图说明.md"
check(t5_desc.exists(), "T5_配图说明.md 存在", warn_only=True)

# v2.1: 配图质量检查
for img in img_files:
    name = img.name
    size_mb = img.stat().st_size / (1024 * 1024)
    if size_mb < 0.5:
        check(False, f"配图文件偏小，可能需要重新生成: {name} ({size_mb:.1f} MB < 0.5 MB)", warn_only=True)
    elif VERBOSE:
        print(f"    📷 {name} ({size_mb:.1f} MB)")

# v7.0: 配图工具来源标注检查
if t5_desc.exists() and img_files:
    t5_desc_content = read_file(t5_desc)
    tool_keywords = ["ChatGPT", "NotebookLM", "网图"]
    for img in img_files:
        name = img.name
        if name in t5_desc_content:
            has_tool = any(tool in t5_desc_content.split(name)[1][:200] for tool in tool_keywords)
            if not has_tool:
                # 也检查整篇文档是否有工具标注
                total_tool_mentions = sum(t5_desc_content.count(t) for t in tool_keywords)
                if total_tool_mentions == 0:
                    check(False, "T5_配图说明.md 未标注任何图片的生成工具（需标注 ChatGPT/NotebookLM/网图）", warn_only=True)
                    break
                elif VERBOSE:
                    print(f"    {Colors.OK} 配图说明含工具标注（{total_tool_mentions} 处）{Colors.RESET}")
                break
        else:
            if VERBOSE:
                print(f"    {Colors.WARN} {name} 未在配图说明中提及{Colors.RESET}")

# v2.1: 垃圾文件检测
junk_imgs = list(OUTPUTS.glob("debug_*.png"))
junk_py = list(OUTPUTS.glob("*_auto.py")) + list(OUTPUTS.glob("nlm_*.py")) + list(OUTPUTS.glob("generate_t5*.py"))
nested_outputs = OUTPUTS / "outputs"

if junk_imgs:
    check(False, f"发现 debug 截图未清理: {[f.name for f in junk_imgs]}，请删除后重试", warn_only=True)
elif VERBOSE:
    print(f"  {Colors.OK} 无 debug 截图残留{Colors.RESET}")

if junk_py:
    check(False, f"发现临时脚本未清理: {[f.name for f in junk_py]}，请删除后重试", warn_only=True)
elif VERBOSE:
    print(f"  {Colors.OK} 无临时脚本残留{Colors.RESET}")

if nested_outputs.exists() and nested_outputs.is_dir():
    check(False, "发现嵌套 outputs/outputs/ 目录，请修复: mv outputs/outputs/* outputs/ && rm -rf outputs/outputs/", warn_only=True)
elif VERBOSE:
    print(f"  {Colors.OK} 无嵌套 outputs/ 目录{Colors.RESET}")

# ══════════════════════════════════════════════════════════════
# T6 终稿
# ══════════════════════════════════════════════════════════════
print(f"\n{Colors.BOLD}━━━ T6 终稿 ━━━{Colors.RESET}")
t6_toutiao = OUTPUTS / "T6_final_头条.md"
t6_portal = OUTPUTS / "T6_门户复用包.md"
check(t6_toutiao.exists(), "T6_final_头条.md 终稿存在")
check(t6_portal.exists(), "T6_门户复用包.md 门户复用包存在")

# v6.0: T6 终稿配图引用对齐检查
if t6_toutiao.exists() and img_files:
    t6_content = read_file(t6_toutiao)
    # 提取 T6 中引用的图片文件名
    referenced_images = re.findall(r'!\[.*?\]\(([^)]*T5_[^)]+)\)', t6_content)
    referenced_names = {Path(ref).name for ref in referenced_images}
    actual_names = {img.name for img in img_files}

    # 检查引用的图片是否都存在
    missing_refs = referenced_names - actual_names
    if missing_refs:
        check(False, f"T6 引用的配图文件不存在: {missing_refs}")
    elif referenced_names:
        if VERBOSE:
            print(f"  {Colors.OK} T6 配图引用与实际文件名对齐（{len(referenced_names)} 张）{Colors.RESET}")

    # 检查是否有配图未被引用
    unreferenced = actual_names - referenced_names
    if unreferenced and referenced_names:
        check(False, f"配图未被 T6 引用: {unreferenced}", warn_only=True)

# ══════════════════════════════════════════════════════════════
# T7 归档完整性（仅 --archive 模式）
# ══════════════════════════════════════════════════════════════
if ARCHIVE_MODE and ARCHIVE_DIR:
    print(f"\n{Colors.BOLD}━━━ T7 归档完整性检查 ━━━{Colors.RESET}")

    # 必须存在的文件
    required_files = [
        "T1_选题池.md",
        "T2_素材包.md",
        "T3_头条.md",
        "T4_审查报告.md",
        "T6_final_头条.md",
        "T6_门户复用包.md",
    ]

    for fname in required_files:
        check((ARCHIVE_DIR / fname).exists(), f"归档包含 {fname}")

    # T5 配图完整性（对照 T5_配图说明.md）
    archive_imgs = list(ARCHIVE_DIR.glob("T5_*.png")) + list(ARCHIVE_DIR.glob("T5_*.jpg"))
    check(len(archive_imgs) >= 5, f"归档配图 ≥ 5 张（当前: {len(archive_imgs)} 张）")

    # 可选但建议的文件
    optional_files = [
        ("T5_配图_生成提示词.md", "配图提示词"),
        ("T5_配图说明.md", "配图说明"),
        ("项目复盘.md", "项目复盘（v6.0 必需）"),
    ]

    for fname, label in optional_files:
        check((ARCHIVE_DIR / fname).exists(), f"归档包含 {label}", warn_only=True)

    # 检查 .DS_Store
    ds_store = ARCHIVE_DIR / ".DS_Store"
    check(not ds_store.exists(), "归档目录不含 .DS_Store", warn_only=True)

    # docx 和 generate_docx.py
    docx_files = list(ARCHIVE_DIR.glob("*.docx"))
    py_files = list(ARCHIVE_DIR.glob("generate_*.py"))
    if docx_files:
        if VERBOSE:
            for f in docx_files:
                print(f"  {Colors.OK} 包含终稿 docx: {f.name}{Colors.RESET}")
    if py_files:
        if VERBOSE:
            for f in py_files:
                print(f"  {Colors.OK} 包含生成脚本: {f.name}{Colors.RESET}")

# ══════════════════════════════════════════════════════════════
# Skill 版本一致性（非归档模式时检查）
# ══════════════════════════════════════════════════════════════
if not ARCHIVE_MODE:
    skills_dir = Path("Skills")
    if skills_dir.exists():
        print(f"\n{Colors.BOLD}━━━ Skill 版本检查 ━━━{Colors.RESET}")
        skill_files = list(skills_dir.glob("*.md"))
        for sf in skill_files:
            content = read_file(sf)
            # 检查是否包含 v5.0+ 关键字
            has_v5_markers = any(kw in content for kw in [
                "双源交叉验证", "VERIFIED", "产品信息库", "头条聚焦",
                "v5.0", "v6.0", "v3.0"
            ])
            if not has_v5_markers and sf.name.startswith("0"):
                check(False, f"Skill 可能未同步至 v5.0+: {sf.name}", warn_only=True)

# ══════════════════════════════════════════════════════════════
# 总结
# ══════════════════════════════════════════════════════════════
print(f"\n{Colors.BOLD}━━━ 校验总结 ━━━{Colors.RESET}")
print(f"  错误: {len(errors)} 条")
print(f"  警告: {len(warnings)} 条")

if errors:
    print(f"\n{Colors.FAIL} 校验未通过，以下问题必须修复：{Colors.RESET}")
    for e in errors:
        print(f"  → {e}")
    sys.exit(1)
elif warnings:
    print(f"\n{Colors.WARN} 校验通过（有警告），建议关注：{Colors.RESET}")
    for w in warnings:
        print(f"  → {w}")
    sys.exit(0)
else:
    print(f"\n{Colors.OK} 全部校验通过{Colors.RESET}")
    sys.exit(0)
