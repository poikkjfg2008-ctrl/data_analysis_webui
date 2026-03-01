#!/usr/bin/env python3
"""
测试数据生成器 - Data Analysis WebUI

生成包含日期和多个数值指标的 Excel 测试文件。
使用方法: python3 create_test_data.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path


def generate_test_excel(output_file: str = "test_data.xlsx", days: int = 365):
    """
    生成测试用 Excel 文件

    Args:
        output_file: 输出文件名
        days: 生成数据的天数
    """
    try:
        import pandas as pd
        import random
    except ImportError as e:
        print(f"❌ 错误: 缺少必要的库 - {e}")
        print("请先安装依赖: pip install pandas openpyxl")
        sys.exit(1)

    print(f"📊 正在生成测试数据（{days} 天）...")

    # 生成日期序列（从今天往前推）
    dates = [datetime.today() - timedelta(days=i) for i in range(days, 0, -1)]

    # 生成带有趋势和波动的模拟数据
    base_production = 1000
    base_sales = 950

    data = {
        '日期': dates,
        '产量': [
            int(base_production + i * 0.3 + random.uniform(-100, 150))
            for i in range(days)
        ],
        '销量': [
            int(base_sales + i * 0.25 + random.uniform(-120, 130))
            for i in range(days)
        ],
        '库存': [random.randint(200, 600) for _ in range(days)],
        '合格率': [round(random.uniform(0.92, 0.99), 4) for _ in range(days)],
        '设备利用率': [round(random.uniform(0.75, 0.95), 4) for _ in range(days)],
    }

    # 添加一些季节性和周期性波动
    for i in range(days):
        # 每周波动
        week_factor = 1.0 + 0.1 * (i % 7) / 7

        # 季节性波动（假设年底高、年初低）
        month = dates[i].month
        seasonal_factor = 1.0 + 0.15 * (month - 6) / 6

        # 应用波动因子
        data['产量'][i] = int(data['产量'][i] * week_factor * seasonal_factor)
        data['销量'][i] = int(data['销量'][i] * week_factor * seasonal_factor)

    # 创建 DataFrame
    df = pd.DataFrame(data)

    # 确保 Excel 输出目录存在
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存到 Excel
    df.to_excel(output_path, index=False)

    print(f"✅ 测试文件已创建: {output_path.absolute()}")
    print(f"\n📈 数据统计:")
    print(f"   - 行数: {len(df)}")
    print(f"   - 列数: {len(df.columns)}")
    print(f"   - 日期范围: {df['日期'].min().date()} 至 {df['日期'].max().date()}")
    print(f"   - 数值列: {', '.join([col for col in df.columns if col != '日期'])}")
    print(f"\n📊 数据预览:")
    print(df.head(10).to_string(index=False))
    print("\n✨ 现在您可以使用此文件测试数据分析功能了！")
    print(f"\n💡 运行分析:")
    print(f"   python skill_build/the_skill_for_this_data_analysis/scripts/call_data_analysis_api.py \\")
    print(f"     --base-url http://127.0.0.1:8001 \\")
    print(f"     --excel-path {output_path.absolute()} \\")
    print(f"     --user-prompt \"分析最近一年产量和销量的趋势\"")

    return str(output_path.absolute())


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="生成测试用 Excel 数据文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                           # 使用默认设置（365天，test_data.xlsx）
  %(prog)s --days 730               # 生成2年的数据
  %(prog)s --output sales_test.xlsx  # 指定输出文件名
  %(prog)s --days 180 --output q1_2024.xlsx  # 自定义天数和文件名
        """
    )

    parser.add_argument(
        '--output', '-o',
        default='test_data.xlsx',
        help='输出 Excel 文件名（默认: test_data.xlsx）'
    )

    parser.add_argument(
        '--days', '-d',
        type=int,
        default=365,
        help='生成数据的天数（默认: 365）'
    )

    args = parser.parse_args()

    # 验证参数
    if args.days <= 0:
        print("❌ 错误: 天数必须大于 0")
        sys.exit(1)

    if args.days > 3650:  # 10年
        print("⚠️  警告: 生成超过10年的数据可能需要较长时间")

    # 生成数据
    try:
        generate_test_excel(args.output, args.days)
    except Exception as e:
        print(f"❌ 生成数据时出错: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
