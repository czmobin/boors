"""
فیلتر نمادهای بورس بر اساس قدرت خریدار
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from api_client import TSETMCClient
from calculator import BourseCalculator
from excel_manager import ExcelManager
from config import MIN_BUYER_POWER_GROWTH


class StockFilter:
    """کلاس اصلی برای فیلتر کردن نمادهای بورس"""

    def __init__(self, symbols_file: str = 'symbols.json'):
        self.symbols_file = symbols_file
        self.api_client = TSETMCClient()
        self.calculator = BourseCalculator()
        self.excel_manager = ExcelManager()
        self.initial_data = {}  # ذخیره داده‌های ابتدای روز
        self.symbols = self._load_symbols()

    def _load_symbols(self) -> List[Dict]:
        """
        بارگذاری لیست نمادها از فایل JSON

        Returns:
            لیست دیکشنری‌های نماد
        """
        try:
            with open(self.symbols_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('symbols', [])
        except Exception as e:
            print(f"خطا در بارگذاری فایل نمادها: {e}")
            return []

    def fetch_and_calculate(self) -> List[Dict]:
        """
        دریافت داده و محاسبه شاخص‌ها برای تمام نمادها

        Returns:
            لیست دیکشنری‌های حاوی اطلاعات محاسبه شده
        """
        results = []

        print(f"\n{'='*50}")
        print(f"زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"در حال دریافت اطلاعات {len(self.symbols)} نماد...")
        print(f"{'='*50}\n")

        for symbol in self.symbols:
            ins_code = symbol.get('insCode')
            name = symbol.get('name', 'نامشخص')

            print(f"در حال پردازش: {name} ({ins_code})")

            # دریافت داده‌ها از API
            data = self.api_client.get_all_data(ins_code)

            if data:
                # محاسبه شاخص‌ها
                metrics = self.calculator.calculate_buyer_power(data['client_type'])

                # ترکیب اطلاعات
                result = {
                    'نماد': name,
                    'کد': ins_code,
                    'زمان': datetime.now().strftime('%H:%M:%S'),
                    'حجم_خرید_حقوقی': metrics['buy_legal_volume'],
                    'حجم_فروش_حقوقی': metrics['sell_legal_volume'],
                    'تعداد_خرید_حقوقی': metrics['buy_legal_count'],
                    'تعداد_فروش_حقوقی': metrics['sell_legal_count'],
                    'ورود_پول_حقوقی_میلیون': metrics['legal_money_flow'],
                    'ورود_پول_حقیقی_میلیون': metrics['real_money_flow'],
                    'قدرت_خریدار': metrics['buyer_power_ratio'],
                    'سرانه_خرید_حقوقی_میلیون': metrics['avg_buy_legal'],
                    'سرانه_فروش_حقوقی_میلیون': metrics['avg_sell_legal'],
                    'ورود_پول_خالص_میلیون': metrics['net_money_flow']
                }

                results.append(result)
                print(f"  ✓ قدرت خریدار: {metrics['buyer_power_ratio']}")
                print(f"  ✓ ورود پول خالص: {metrics['net_money_flow']} میلیون")

        return results

    def filter_by_growth(self, current_data: List[Dict]) -> List[Dict]:
        """
        فیلتر نمادهایی که قدرت خریدارشان نسبت به ابتدای روز رشد کرده

        Args:
            current_data: داده‌های فعلی

        Returns:
            لیست نمادهای فیلتر شده
        """
        if not self.initial_data:
            print("هنوز داده ابتدای روز موجود نیست")
            return []

        filtered = []

        for current in current_data:
            ins_code = current['کد']

            # پیدا کردن داده اولیه این نماد
            initial = self.initial_data.get(ins_code)

            if initial:
                initial_power = initial.get('قدرت_خریدار', 0)
                current_power = current.get('قدرت_خریدار', 0)

                # محاسبه درصد رشد
                growth = self.calculator.calculate_growth(initial_power, current_power)

                # اضافه کردن درصد رشد به داده
                current['رشد_قدرت_خریدار_درصد'] = growth
                current['قدرت_خریدار_اولیه'] = initial_power

                # فیلتر بر اساس حداقل رشد
                if growth >= MIN_BUYER_POWER_GROWTH * 100:
                    filtered.append(current)

        # مرتب‌سازی بر اساس رشد (نزولی)
        filtered.sort(key=lambda x: x['رشد_قدرت_خریدار_درصد'], reverse=True)

        return filtered

    def run_once(self, save_as_initial: bool = False) -> None:
        """
        یک بار اجرا و ذخیره داده

        Args:
            save_as_initial: آیا این داده را به عنوان داده اولیه ذخیره کنیم؟
        """
        # دریافت و محاسبه داده‌ها
        data = self.fetch_and_calculate()

        if not data:
            print("هیچ داده‌ای دریافت نشد")
            return

        # ذخیره داده‌های اولیه
        if save_as_initial or not self.initial_data:
            self.initial_data = {item['کد']: item for item in data}
            print(f"\n✓ داده‌های اولیه برای {len(self.initial_data)} نماد ذخیره شد")

        # ذخیره در Excel
        self.excel_manager.save_data(data)

        # فیلتر و نمایش نمادهای رشد کرده
        if self.initial_data and not save_as_initial:
            filtered = self.filter_by_growth(data)

            if filtered:
                print(f"\n{'='*50}")
                print(f"نمادهای با رشد قدرت خریدار (بیش از {MIN_BUYER_POWER_GROWTH*100}%):")
                print(f"{'='*50}")

                for item in filtered:
                    print(f"\n{item['نماد']}:")
                    print(f"  - قدرت خریدار اولیه: {item['قدرت_خریدار_اولیه']}")
                    print(f"  - قدرت خریدار فعلی: {item['قدرت_خریدار']}")
                    print(f"  - رشد: {item['رشد_قدرت_خریدار_درصد']}%")
                    print(f"  - ورود پول خالص: {item['ورود_پول_خالص_میلیون']} میلیون")

                # ذخیره نمادهای فیلتر شده در شیت جداگانه
                self.excel_manager.create_summary_sheet(filtered)
            else:
                print(f"\nهیچ نمادی با رشد بیش از {MIN_BUYER_POWER_GROWTH*100}% پیدا نشد")
