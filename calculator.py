"""
محاسبه قدرت خریدار و ورود پول
"""

from typing import Dict, Optional


class BourseCalculator:
    """کلاس برای محاسبات مربوط به بورس"""

    @staticmethod
    def _get_field(data: Dict, *field_names) -> any:
        """
        دریافت مقدار فیلد با چک کردن نام‌های مختلف (case-insensitive)

        Args:
            data: دیکشنری داده
            field_names: نام‌های مختلف فیلد برای جستجو

        Returns:
            مقدار فیلد یا 0
        """
        for name in field_names:
            # جستجوی case-insensitive
            for key in data.keys():
                if key.lower() == name.lower():
                    return data[key]
        return 0

    @staticmethod
    def calculate_buyer_power(client_type_data: Dict) -> Dict:
        """
        محاسبه قدرت خریدار بر اساس داده‌های حقیقی و حقوقی

        Supports both formats:
        - Old TSETMC: {'clientType': {'buy_N_Volume': ...}}
        - New BrsApi: {'Buy_N_Volume': ...}

        Args:
            client_type_data: داده‌های حقیقی/حقوقی از API

        Returns:
            دیکشنری شامل شاخص‌های قدرت خریدار
        """
        # پشتیبانی از فرمت قدیمی TSETMC
        if 'clientType' in client_type_data:
            ct = client_type_data['clientType']
        else:
            # فرمت جدید BrsApi - داده‌ها مستقیماً در سطح اول هستند
            ct = client_type_data

        # استفاده از helper برای دریافت فیلدها (case-insensitive)
        calc = BourseCalculator()

        # حجم خرید و فروش حقوقی
        buy_legal_volume = float(calc._get_field(ct, 'buy_N_Volume', 'Buy_N_Volume'))
        sell_legal_volume = float(calc._get_field(ct, 'sell_N_Volume', 'Sell_N_Volume'))

        # تعداد خرید و فروش حقوقی
        buy_legal_count = int(calc._get_field(ct, 'buy_CountN', 'Buy_CountN'))
        sell_legal_count = int(calc._get_field(ct, 'sell_CountN', 'Sell_CountN'))

        # حجم خرید و فروش حقیقی
        buy_real_volume = float(calc._get_field(ct, 'buy_I_Volume', 'Buy_I_Volume'))
        sell_real_volume = float(calc._get_field(ct, 'sell_I_Volume', 'Sell_I_Volume'))

        # تعداد خرید و فروش حقیقی
        buy_real_count = int(calc._get_field(ct, 'buy_CountI', 'Buy_CountI'))
        sell_real_count = int(calc._get_field(ct, 'sell_CountI', 'Sell_CountI'))

        # محاسبه ورود/خروج پول حقوقی (به میلیون)
        legal_money_flow = (buy_legal_volume - sell_legal_volume) / 1_000_000

        # محاسبه ورود/خروج پول حقیقی (به میلیون) - معکوس است
        real_money_flow = (sell_real_volume - buy_real_volume) / 1_000_000

        # محاسبه قدرت خریدار (نسبت خرید حقوقی به فروش)
        if sell_legal_volume > 0:
            buyer_power_ratio = buy_legal_volume / sell_legal_volume
        elif buy_legal_volume > 0:
            # اگر فروش صفر باشه ولی خرید داشته باشیم، عدد بزرگ (قدرت خیلی بالا)
            buyer_power_ratio = 999.99
        else:
            # هم خرید و هم فروش صفر
            buyer_power_ratio = 0

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
            # اگر مقدار اولیه صفر بود
            if current_value == 0:
                return 0
            else:
                # رشد خیلی زیاد (از صفر شروع کرده)
                return 999.99

        growth = ((current_value - initial_value) / abs(initial_value)) * 100
        return round(growth, 2)
