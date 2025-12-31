"""
فیلتر نمادهای بورس بر اساس قدرت خریدار - نسخه BrsApi
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from brsapi_client import BrsApiClient
from calculator import BourseCalculator
from excel_manager import ExcelManager
from config import MIN_BUYER_POWER_GROWTH


class StockFilter:
    """کلاس اصلی برای فیلتر کردن نمادهای بورس"""

    def __init__(self, symbols_file: str = 'symbols.json'):
        self.symbols_file = symbols_file
        self.api_client = BrsApiClient()
        self.calculator = BourseCalculator()
        self.excel_manager = ExcelManager()
        self.initial_data = {}  # ذخیره داده‌های ابتدای روز
        self.symbols = self._load_symbols()

        # Cache برای داده‌های تمام نمادها
        self.all_symbols_cache = None
        self.cache_time = None

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

    def _get_all_symbols_data(self, force_refresh: bool = False) -> Optional[List[Dict]]:
        """
        دریافت داده‌های تمام نمادها (با cache)

        Args:
            force_refresh: آیا cache را نادیده بگیریم و داده جدید بگیریم؟

        Returns:
            لیست تمام نمادها
        """
        # اگر cache موجود است و نیاز به refresh نیست
        if not force_refresh and self.all_symbols_cache is not None:
            return self.all_symbols_cache

        # دریافت داده‌های جدید
        print("📡 در حال دریافت داده‌های تمام نمادها از BrsApi...")
        data = self.api_client.get_all_symbols()

        if data:
            self.all_symbols_cache = data
            self.cache_time = datetime.now()
            print(f"✅ {len(data)} نماد دریافت شد")
            return data

        print("❌ خطا در دریافت داده‌ها")
        return None

    def fetch_and_calculate(self, force_refresh: bool = False) -> List[Dict]:
        """
        دریافت داده و محاسبه شاخص‌ها برای نمادهای انتخاب شده

        Args:
            force_refresh: آیا cache را نادیده بگیریم؟

        Returns:
            لیست دیکشنری‌های حاوی اطلاعات محاسبه شده
        """
        results = []

        print(f"\n{'='*50}")
        print(f"زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"در حال پردازش {len(self.symbols)} نماد...")
        print(f"{'='*50}\n")

        # دریافت تمام نمادها یک بار
        all_data = self._get_all_symbols_data(force_refresh)

        if not all_data:
            return []

        # پردازش فقط نمادهای انتخاب شده
        for symbol_config in self.symbols:
            symbol_id = symbol_config.get('id') or symbol_config.get('insCode')
            ticker = symbol_config.get('ticker', '')
            name = symbol_config.get('name', 'نامشخص')

            print(f"در حال پردازش: {name} ({ticker})")

            # جستجوی نماد در داده‌های دریافتی
            symbol_data = None

            for item in all_data:
                # جستجو با ticker (نماد کوتاه)
                if item.get('l18') == ticker:
                    symbol_data = item
                    break
                # یا جستجو با id (اگر موجود باشد)
                elif symbol_id and str(item.get('id')) == str(symbol_id):
                    symbol_data = item
                    break

            if not symbol_data:
                print(f"  ⚠️  نماد یافت نشد")
                continue

            # محاسبه شاخص‌ها
            metrics = self.calculator.calculate_buyer_power(symbol_data)

            # ترکیب اطلاعات
            result = {
                'نماد': ticker or symbol_data.get('l18', 'N/A'),
                'نام_کامل': name,
                'کد': str(symbol_data.get('id', 'N/A')),
                'زمان': datetime.now().strftime('%H:%M:%S'),
                'قیمت_پایانی': symbol_data.get('pc', 0),
                'درصد_تغییر': symbol_data.get('pcp', 0),
                'حجم_معاملات': symbol_data.get('tvol', 0),
                'ارزش_معاملات': symbol_data.get('tval', 0),
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
            print(f"  ✓ ورود پول خالص: {metrics['net_money_flow']:,.0f} میلیون")

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
            symbol_code = current['کد']

            # پیدا کردن داده اولیه این نماد
            initial = self.initial_data.get(symbol_code)

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

    def run_once(self, save_as_initial: bool = False, force_refresh: bool = False) -> None:
        """
        یک بار اجرا و ذخیره داده

        Args:
            save_as_initial: آیا این داده را به عنوان داده اولیه ذخیره کنیم؟
            force_refresh: آیا cache را نادیده بگیریم؟
        """
        # دریافت و محاسبه داده‌ها
        data = self.fetch_and_calculate(force_refresh)

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
                    print(f"  - ورود پول خالص: {item['ورود_پول_خالص_میلیون']:,.0f} میلیون")

                # ذخیره نمادهای فیلتر شده در شیت جداگانه
                self.excel_manager.create_summary_sheet(filtered)
            else:
                print(f"\nهیچ نمادی با رشد بیش از {MIN_BUYER_POWER_GROWTH*100}% پیدا نشد")
