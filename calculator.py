"""
محاسبه قدرت خریدار و ورود پول
"""

from typing import Dict, Optional


class BourseCalculator:
    """کلاس برای محاسبات مربوط به بورس"""

    @staticmethod
    def calculate_buyer_power(client_type_data: Dict) -> Dict:
        """
        محاسبه قدرت خریدار بر اساس داده‌های حقیقی و حقوقی

        Args:
            client_type_data: داده‌های clientType از API

        Returns:
            دیکشنری شامل شاخص‌های قدرت خریدار
        """
        ct = client_type_data.get('clientType', {})

        # حجم خرید و فروش حقوقی
        buy_legal_volume = float(ct.get('buy_N_Volume', 0))
        sell_legal_volume = float(ct.get('sell_N_Volume', 0))

        # تعداد خرید و فروش حقوقی
        buy_legal_count = int(ct.get('buy_CountN', 0))
        sell_legal_count = int(ct.get('sell_CountN', 0))

        # حجم خرید و فروش حقیقی
        buy_real_volume = float(ct.get('buy_I_Volume', 0))
        sell_real_volume = float(ct.get('sell_I_Volume', 0))

        # تعداد خرید و فروش حقیقی
        buy_real_count = int(ct.get('buy_CountI', 0))
        sell_real_count = int(ct.get('sell_CountI', 0))

        # محاسبه ورود/خروج پول حقوقی (به میلیون)
        legal_money_flow = (buy_legal_volume - sell_legal_volume) / 1_000_000

        # محاسبه ورود/خروج پول حقیقی (به میلیون) - معکوس است
        real_money_flow = (sell_real_volume - buy_real_volume) / 1_000_000

        # محاسبه قدرت خریدار (نسبت خرید حقوقی به فروش)
        if sell_legal_volume > 0:
            buyer_power_ratio = buy_legal_volume / sell_legal_volume
        else:
            buyer_power_ratio = float('inf') if buy_legal_volume > 0 else 0

        # سرانه خرید حقوقی (به میلیون تومان)
        avg_buy_legal = (buy_legal_volume / buy_legal_count / 1_000_000) if buy_legal_count > 0 else 0

        # سرانه فروش حقوقی (به میلیون تومان)
        avg_sell_legal = (sell_legal_volume / sell_legal_count / 1_000_000) if sell_legal_count > 0 else 0

        return {
            'buy_legal_volume': buy_legal_volume,
            'sell_legal_volume': sell_legal_volume,
            'buy_legal_count': buy_legal_count,
            'sell_legal_count': sell_legal_count,
            'buy_real_volume': buy_real_volume,
            'sell_real_volume': sell_real_volume,
            'buy_real_count': buy_real_count,
            'sell_real_count': sell_real_count,
            'legal_money_flow': round(legal_money_flow, 2),
            'real_money_flow': round(real_money_flow, 2),
            'buyer_power_ratio': round(buyer_power_ratio, 2),
            'avg_buy_legal': round(avg_buy_legal, 2),
            'avg_sell_legal': round(avg_sell_legal, 2),
            'net_money_flow': round(legal_money_flow, 2)  # ورود پول خالص (حقوقی)
        }

    @staticmethod
    def calculate_growth(initial_value: float, current_value: float) -> float:
        """
        محاسبه درصد رشد

        Args:
            initial_value: مقدار اولیه
            current_value: مقدار فعلی

        Returns:
            درصد رشد
        """
        if initial_value == 0:
            return 0 if current_value == 0 else float('inf')

        growth = ((current_value - initial_value) / abs(initial_value)) * 100
        return round(growth, 2)
