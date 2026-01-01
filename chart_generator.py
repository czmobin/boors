#!/usr/bin/env python3
"""
ساخت نمودارهای روند قدرت خریدار
"""

import matplotlib
matplotlib.use('Agg')  # Backend بدون GUI
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Dict, Optional
import io


class ChartGenerator:
    """کلاس برای ساخت نمودارهای تحلیلی"""

    def __init__(self):
        # تنظیمات فونت برای فارسی (بدون نیاز به فونت خاص)
        plt.rcParams['axes.unicode_minus'] = False

    def generate_trend_chart(self, history: List[Dict], symbol_code: str, symbol_name: str) -> Optional[bytes]:
        """
        ساخت نمودار روند قدرت خریدار برای یک نماد

        Args:
            history: لیست snapshot‌های history
            symbol_code: کد نماد
            symbol_name: نام نماد

        Returns:
            bytes تصویر PNG یا None اگر داده کافی نباشد
        """
        if len(history) < 2:
            return None

        # استخراج داده‌ها
        timestamps = []
        powers = []

        for snapshot in history:
            if symbol_code in snapshot['data']:
                power = snapshot['data'][symbol_code].get('قدرت_خریدار', 0)
                timestamp = snapshot['timestamp']
                timestamps.append(timestamp)
                powers.append(power)

        if len(timestamps) < 2:
            return None

        # ساخت نمودار
        fig, ax = plt.subplots(figsize=(10, 6))

        # رسم خط روند
        ax.plot(timestamps, powers, marker='o', linewidth=2, markersize=8, color='#2196F3')

        # تنظیمات محورها
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Buyer Power', fontsize=12)
        ax.set_title(f'Trend: {symbol_name} ({symbol_code})', fontsize=14, fontweight='bold')

        # Grid
        ax.grid(True, alpha=0.3, linestyle='--')

        # فرمت زمان
        ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()

        # ذخیره به buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

    def generate_multi_symbol_chart(self, history: List[Dict], symbols: List[tuple]) -> Optional[bytes]:
        """
        ساخت نمودار مقایسه چند نماد

        Args:
            history: لیست snapshot‌های history
            symbols: لیست tuple‌های (code, name)

        Returns:
            bytes تصویر PNG یا None
        """
        if len(history) < 2 or not symbols:
            return None

        fig, ax = plt.subplots(figsize=(12, 7))

        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4']

        for idx, (code, name) in enumerate(symbols[:6]):  # حداکثر 6 نماد
            timestamps = []
            powers = []

            for snapshot in history:
                if code in snapshot['data']:
                    power = snapshot['data'][code].get('قدرت_خریدار', 0)
                    timestamp = snapshot['timestamp']
                    timestamps.append(timestamp)
                    powers.append(power)

            if len(timestamps) >= 2:
                color = colors[idx % len(colors)]
                ax.plot(timestamps, powers, marker='o', linewidth=2, markersize=6,
                       label=f'{name}', color=color)

        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Buyer Power', fontsize=12)
        ax.set_title('Comparison: Multiple Symbols', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()

    def generate_top_symbols_chart(self, history: List[Dict], top_n: int = 5) -> Optional[bytes]:
        """
        نمودار برترین نمادها بر اساس آخرین قدرت خریدار

        Args:
            history: لیست snapshot‌های history
            top_n: تعداد نمادهای برتر

        Returns:
            bytes تصویر PNG
        """
        if not history:
            return None

        # آخرین snapshot
        latest = history[-1]
        data = latest['data']

        # مرتب‌سازی بر اساس قدرت خریدار
        sorted_items = sorted(data.items(), key=lambda x: x[1].get('قدرت_خریدار', 0), reverse=True)
        top_items = sorted_items[:top_n]

        if not top_items:
            return None

        # استخراج داده‌ها
        names = []
        powers = []

        for item in top_items:
            # item[0] = کد نماد، item[1] = دیکشنری داده‌ها
            symbol_data = item[1]
            symbol_name = symbol_data.get('نماد', 'N/A')
            symbol_power = symbol_data.get('قدرت_خریدار', 0)

            # محدود کردن طول نام برای نمایش بهتر
            if len(symbol_name) > 10:
                symbol_name = symbol_name[:10]

            names.append(symbol_name)
            powers.append(symbol_power)

        # معکوس کردن لیست برای نمایش صحیح (بزرگترین بالا)
        # چون barh از پایین به بالا نمایش میده
        names.reverse()
        powers.reverse()

        # ساخت نمودار میله‌ای
        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.barh(names, powers, color='#4CAF50')

        # رنگ‌آمیزی gradient (معکوس برای نمایش صحیح - بزرگترین پررنگ‌تر)
        for i, bar in enumerate(bars):
            # از بالا به پایین رنگ کم‌رنگ‌تر میشه
            bar.set_color(plt.cm.Greens(1.0 - (i / len(bars)) * 0.6))

        ax.set_xlabel('Buyer Power', fontsize=12)
        ax.set_title(f'Top {top_n} Symbols by Buyer Power', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x', linestyle='--')
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        return buf.getvalue()
