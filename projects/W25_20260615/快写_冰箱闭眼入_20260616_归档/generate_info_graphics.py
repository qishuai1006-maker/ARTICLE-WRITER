import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

# 针对 MacOS 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti TC']
plt.rcParams['axes.unicode_minus'] = False

output_dir = '/Users/ltn/Library/CloudStorage/GoogleDrive-qishuai1006@gmail.com/我的云端硬盘/Super Writer/outputs'

def create_table_infographic():
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    fig.patch.set_facecolor('#F5F7FA') # 高级灰白背景
    ax.axis('off')
    
    # Title
    plt.text(0.5, 0.92, "2026年 5款【闭眼入】高性价比冰箱清单", ha='center', va='center', fontsize=24, fontweight='bold', color='#1A1F36')
    plt.text(0.5, 0.86, "牛科技严选 · 拒绝参数忽悠，只推真实体验", ha='center', va='center', fontsize=12, color='#697386')
    
    # Table data
    data = [
        ["预算段", "首推型号", "核心技术/参数", "最适合人群"],
        ["3500-4000元", "华凌 518升", "双系统 / 自动制冰 / PST+", "追求极致性价比、爱喝冰饮"],
        ["4000-5000元", "海尔 503云溪", "全空间保鲜 / EPP杀菌", "看重食材保鲜、绿叶菜囤货"],
        ["5000-6000元", "美的 555机皇版", "双系统2.0 / 60分钟速冰", "人口多、要求不串味的干饭人"],
        ["6000-8000元", "海尔 630云溪MAX", "594mm真平嵌 / 10kg大冷冻力", "做现代嵌入式橱柜的大户型"],
        ["8000-1万元", "卡萨帝 517揽光", "MRA低氧窖藏 / 十字奢华门", "高端食材多、追求顶级质感"]
    ]
    
    # Create Table
    table = ax.table(cellText=data, loc='center', cellLoc='center', bbox=[0.05, 0.1, 0.9, 0.7])
    
    # Style table
    table.auto_set_font_size(False)
    table.set_fontsize(14)
    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor('none') # 去除默认黑框
        if i == 0:
            cell.set_text_props(weight='bold', color='white', fontsize=15)
            cell.set_facecolor('#0066FF') # 科技蓝表头
        else:
            cell.set_facecolor('#FFFFFF' if i % 2 == 0 else '#F0F4F8')
            cell.set_text_props(color='#3C4257')
        
        # Add subtle bottom border to rows
        if i > 0:
            cell.set_edgecolor('#E3E8EE')
            cell.set_linewidth(1)
            cell.visible_edges = 'B'
            
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '信息图1_参数对比.png'), bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

def create_checklist_infographic():
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    fig.patch.set_facecolor('#111827') # 深色高级科技风背景
    ax.axis('off')
    
    plt.text(0.5, 0.90, "买冰箱绝对不踩坑的 4 条底线", ha='center', va='center', fontsize=26, fontweight='bold', color='#FFFFFF')
    plt.text(0.5, 0.82, "低于这个配置的，导购吹破天也别买", ha='center', va='center', fontsize=13, color='#9CA3AF')
    
    rules = [
        ("必须买【双系统】", "冷藏冷冻独立循环，榴莲大葱不串味"),
        ("嵌入必选【真平嵌】", "厚度≤600mm且底部散热，完美齐平不凸出"),
        ("认准【一级能效】", "冰箱24小时开机，二级/三级常年电费亏死"),
        ("强烈推荐【自动制冰】", "夏天极大提升幸福感的实用神器")
    ]
    
    y = 0.65
    for title, desc in rules:
        # Card background
        rect = patches.Rectangle((0.1, y - 0.08), 0.8, 0.14, linewidth=0, facecolor='#1F2937')
        ax.add_patch(rect)
        
        # Icon / Accent bar
        accent = patches.Rectangle((0.1, y - 0.08), 0.015, 0.14, linewidth=0, facecolor='#10B981')
        ax.add_patch(accent)
        
        # Text
        plt.text(0.14, y + 0.02, title, ha='left', va='center', fontsize=16, color='#F9FAFB', weight='bold')
        plt.text(0.14, y - 0.03, desc, ha='left', va='center', fontsize=13, color='#D1D5DB')
        y -= 0.16
        
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, '信息图2_避坑底线.png'), bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

try:
    create_table_infographic()
    create_checklist_infographic()
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
