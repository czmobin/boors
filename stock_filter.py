"""
فیلتر نمادهای بورس بر اساس قدرت خریدار - نسخه BrsApi
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from collections import deque
from brsapi_client import BrsApiClient
from calculator import BourseCalculator
from excel_manager import ExcelManager
from config import (
    MIN_BUYER_POWER_GROWTH,
    MIN_POSITIVE_GROWTH,
    MIN_SIGNIFICANT_GROWTH,
    MAX_HISTORY_SIZE,
    MIN_SLOPE_SAMPLES
)


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

        # History برای محاسبه شیب (تغییرات زمانی)
        # هر آیتم: {'timestamp': datetime, 'data': {code: {'قدرت_خریدار': ...}}}
        self.history = deque(maxlen=MAX_HISTORY_SIZE)

    def _load_symbols(self) -> List[Dict]:
        """
        بارگذاری لیست نمادها از فایل JSON

        اگر symbols خالی باشد یا "process_all": true باشد، همه نمادها پردازش می‌شوند

        Returns:
            لیست دیکشنری‌های نماد
        """
        try:
            with open(self.symbols_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # چک کردن فلگ process_all
                if data.get('process_all', False):
                    print("⚙️  حالت 'همه نمادها' فعال است")
                    return []  # خالی برگردان تا همه پردازش شوند

                symbols = data.get('symbols', [])

                if not symbols:
                    print("⚠️  لیست نمادها خالی است - همه نمادها پردازش می‌شوند")

                return symbols
        except Exception as e:
            print(f"خطا در بارگذاری فایل نمادها: {e}")
            return []

    def _get_all_symbols_data(self, force_refresh: bool = False, date: str = None) -> Optional[List[Dict]]:
        """
        دریافت داده‌های تمام نمادها (با cache)

        Args:
            force_refresh: آیا cache را نادیده بگیریم و داده جدید بگیریم؟
            date: تاریخ به فرمت YYYY-MM-DD (برای داده تاریخی)

        Returns:
            لیست تمام نمادها
        """
        # اگر تاریخ داده شده، همیشه refresh کن (cache نکن)
        if date:
            force_refresh = True

        # اگر cache موجود است و نیاز به refresh نیست
        if not force_refresh and self.all_symbols_cache is not None:
            return self.all_symbols_cache

        # دریافت داده‌های جدید
        if date:
            print(f"📡 در حال دریافت داده‌های تاریخ {date} از BrsApi...")
        else:
            print("📡 در حال دریافت داده‌های تمام نمادها از BrsApi...")

        data = self.api_client.get_all_symbols(date=date)

        if data:
            # فقط اگر تاریخ نداشتیم، cache کن
            if not date:
                self.all_symbols_cache = data
                self.cache_time = datetime.now()
            print(f"✅ {len(data)} نماد دریافت شد")
            return data

        print("❌ خطا در دریافت داده‌ها")
        return None

    def fetch_and_calculate(self, force_refresh: bool = False, date: str = None) -> List[Dict]:
        """
        دریافت داده و محاسبه شاخص‌ها برای نمادهای انتخاب شده

        Args:
            force_refresh: آیا cache را نادیده بگیریم؟
            date: تاریخ به فرمت YYYY-MM-DD (برای داده تاریخی)

        Returns:
            لیست دیکشنری‌های حاوی اطلاعات محاسبه شده
        """
        results = []

        # دریافت تمام نمادها یک بار
        all_data = self._get_all_symbols_data(force_refresh, date=date)

        if not all_data:
            return []

        # اگر symbols خالی باشد، همه نمادها رو پردازش کن
        process_all = len(self.symbols) == 0

        if process_all:
            symbols_to_process = all_data
            print(f"\n{'='*50}")
            print(f"زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⚙️  حالت پردازش همه نمادها")
            print(f"در حال پردازش {len(symbols_to_process)} نماد...")
            print(f"{'='*50}\n")
        else:
            symbols_to_process = self.symbols
            print(f"\n{'='*50}")
            print(f"زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"در حال پردازش {len(symbols_to_process)} نماد انتخابی...")
            print(f"{'='*50}\n")

        # پردازش نمادها
        for idx, item in enumerate(symbols_to_process, 1):
            if process_all:
                # داده مستقیماً از all_data
                symbol_data = item
                ticker = symbol_data.get('l18', 'N/A')
                name = symbol_data.get('l30', 'نامشخص')

                # نمایش پیشرفت هر 100 نماد
                if idx % 100 == 0:
                    print(f"پردازش شده: {idx}/{len(symbols_to_process)}")
            else:
                # جستجو بر اساس config
                symbol_config = item
                symbol_id = symbol_config.get('id') or symbol_config.get('insCode')
                ticker = symbol_config.get('ticker', '')
                name = symbol_config.get('name', 'نامشخص')

                print(f"در حال پردازش: {name} ({ticker})")

                # جستجوی نماد در داده‌های دریافتی
                symbol_data = None

                for data_item in all_data:
                    # جستجو با ticker (نماد کوتاه)
                    if data_item.get('l18') == ticker:
                        symbol_data = data_item
                        break
                    # یا جستجو با id (اگر موجود باشد)
                    elif symbol_id and str(data_item.get('id')) == str(symbol_id):
                        symbol_data = data_item
                        break

                if not symbol_data:
                    print(f"  ⚠️  نماد یافت نشد")
                    continue

            # محاسبه شاخص‌ها
            try:
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
                    # داده‌های حقیقی (برای محاسبه قدرت خریدار)
                    'حجم_خرید_حقیقی': metrics['buy_real_volume'],
                    'تعداد_خرید_حقیقی': metrics['buy_real_count'],
                    'حجم_فروش_حقیقی': metrics['sell_real_volume'],
                    'تعداد_فروش_حقیقی': metrics['sell_real_count'],
                    # داده‌های حقوقی
                    'حجم_خرید_حقوقی': metrics['buy_legal_volume'],
                    'حجم_فروش_حقوقی': metrics['sell_legal_volume'],
                    'تعداد_خرید_حقوقی': metrics['buy_legal_count'],
                    'تعداد_فروش_حقوقی': metrics['sell_legal_count'],
                    # محاسبات
                    'X_سرانه_خرید_حقیقی_تومان': metrics['x_avg_buy_real_toman'],
                    'Y_سرانه_فروش_حقیقی_تومان': metrics['y_avg_sell_real_toman'],
                    'تفاضل_سرانه_تومان': metrics['diff_avg_real_toman'],
                    'قدرت_خریدار': metrics['buyer_power_ratio'],
                    'ورود_پول_حقوقی_میلیون': metrics['legal_money_flow'],
                    'ورود_پول_حقیقی_میلیون': metrics['real_money_flow'],
                    'سرانه_خرید_حقوقی_میلیون': metrics['avg_buy_legal'],
                    'سرانه_فروش_حقوقی_میلیون': metrics['avg_sell_legal'],
                    'ورود_پول_خالص_میلیون': metrics['net_money_flow']
                }

                results.append(result)

                if not process_all:
                    print(f"  ✓ قدرت خریدار: {metrics['buyer_power_ratio']}")
                    print(f"  ✓ ورود پول خالص: {metrics['net_money_flow']:,.0f} میلیون")

            except Exception as e:
                if not process_all:
                    print(f"  ❌ خطا: {e}")
                continue

        print(f"\n✅ پردازش کامل شد: {len(results)} نماد")

        # اضافه کردن به history (فقط برای اسکن‌های فعلی، نه تاریخی)
        if not date and results:
            self.add_to_history(results)

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

    # متدهای مدیریت نمادها
    def add_symbol(self, name: str, ticker: str) -> bool:
        """
        اضافه کردن نماد جدید به لیست

        Args:
            name: نام کامل نماد
            ticker: نماد کوتاه (ticker)

        Returns:
            True اگر موفق بود، False در غیر این صورت
        """
        try:
            # بررسی تکراری نبودن ticker
            for symbol in self.symbols:
                if symbol.get('ticker', '').strip() == ticker.strip():
                    print(f"⚠️  نماد {ticker} قبلا وجود دارد")
                    return False

            # اضافه کردن نماد جدید
            new_symbol = {
                "name": name.strip(),
                "ticker": ticker.strip(),
                "id": None
            }
            self.symbols.append(new_symbol)

            # ذخیره در فایل
            return self.save_symbols()

        except Exception as e:
            print(f"❌ خطا در اضافه کردن نماد: {e}")
            return False

    def remove_symbol(self, ticker: str) -> bool:
        """
        حذف نماد از لیست

        Args:
            ticker: نماد کوتاه برای حذف

        Returns:
            True اگر موفق بود، False در غیر این صورت
        """
        try:
            # پیدا کردن و حذف نماد
            initial_count = len(self.symbols)
            self.symbols = [s for s in self.symbols if s.get('ticker', '').strip() != ticker.strip()]

            if len(self.symbols) == initial_count:
                print(f"⚠️  نماد {ticker} یافت نشد")
                return False

            # ذخیره در فایل
            return self.save_symbols()

        except Exception as e:
            print(f"❌ خطا در حذف نماد: {e}")
            return False

    def update_symbol(self, ticker: str, new_name: str) -> bool:
        """
        ویرایش نام نماد

        Args:
            ticker: نماد کوتاه
            new_name: نام جدید

        Returns:
            True اگر موفق بود، False در غیر این صورت
        """
        try:
            # پیدا کردن و ویرایش نماد
            found = False
            for symbol in self.symbols:
                if symbol.get('ticker', '').strip() == ticker.strip():
                    symbol['name'] = new_name.strip()
                    found = True
                    break

            if not found:
                print(f"⚠️  نماد {ticker} یافت نشد")
                return False

            # ذخیره در فایل
            return self.save_symbols()

        except Exception as e:
            print(f"❌ خطا در ویرایش نماد: {e}")
            return False

    def save_symbols(self) -> bool:
        """
        ذخیره لیست نمادها در فایل JSON

        Returns:
            True اگر موفق بود، False در غیر این صورت
        """
        try:
            # خواندن فایل فعلی برای حفظ کامنت‌ها
            with open(self.symbols_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # به‌روزرسانی symbols
            data['symbols'] = self.symbols

            # ذخیره در فایل
            with open(self.symbols_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ لیست نمادها ذخیره شد ({len(self.symbols)} نماد)")
            return True

        except Exception as e:
            print(f"❌ خطا در ذخیره فایل نمادها: {e}")
            return False

    def get_symbols(self) -> List[Dict]:
        """
        دریافت لیست نمادها

        Returns:
            لیست نمادها
        """
        return self.symbols

    # متدهای مدیریت History و محاسبه شیب
    def add_to_history(self, data: List[Dict]) -> None:
        """
        اضافه کردن snapshot جدید به history

        Args:
            data: لیست داده‌های نمادها
        """
        snapshot = {
            'timestamp': datetime.now(),
            'data': {item['کد']: item for item in data}
        }
        self.history.append(snapshot)
        print(f"📊 History updated: {len(self.history)} snapshots")

    def calculate_slope(self, symbol_code: str) -> Optional[float]:
        """
        محاسبه شیب تغییرات قدرت خریدار برای یک نماد

        از رگرسیون خطی ساده استفاده می‌کنیم

        Args:
            symbol_code: کد نماد

        Returns:
            شیب (مثبت = رو به بالا، منفی = رو به پایین، None = داده کافی نیست)
        """
        if len(self.history) < MIN_SLOPE_SAMPLES:
            return None

        # استخراج نقاط (timestamp, قدرت_خریدار)
        points = []
        for snapshot in self.history:
            if symbol_code in snapshot['data']:
                power = snapshot['data'][symbol_code].get('قدرت_خریدار', 0)
                timestamp = snapshot['timestamp']
                points.append((timestamp, power))

        if len(points) < MIN_SLOPE_SAMPLES:
            return None

        # محاسبه شیب با رگرسیون خطی
        # تبدیل timestamp به عدد (ثانیه از اولین نقطه)
        base_time = points[0][0]
        x_values = [(p[0] - base_time).total_seconds() for p in points]
        y_values = [p[1] for p in points]

        n = len(points)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)

        # فرمول شیب: (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x^2)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def filter_with_slope(self, data: List[Dict], filter_type: str = 'positive_gentle') -> List[Dict]:
        """
        فیلتر نمادها بر اساس رشد و شیب

        Args:
            data: داده‌های فعلی
            filter_type: نوع فیلتر
                - 'positive_gentle': رشد مثبت با شیب ملایم (>0)
                - 'significant_upward': رشد بیش از 10% با شیب رو به بالا

        Returns:
            لیست نمادهای فیلتر شده
        """
        if not self.initial_data:
            print("⚠️  داده اولیه موجود نیست. ابتدا یک اسکن اولیه انجام دهید.")
            return []

        filtered = []

        for current in data:
            symbol_code = current['کد']
            symbol_name = current['نماد']

            # پیدا کردن داده اولیه
            initial = self.initial_data.get(symbol_code)
            if not initial:
                continue

            initial_power = initial.get('قدرت_خریدار', 0)
            current_power = current.get('قدرت_خریدار', 0)

            # محاسبه درصد رشد
            growth = self.calculator.calculate_growth(initial_power, current_power)

            # محاسبه شیب
            slope = self.calculate_slope(symbol_code)

            # اضافه کردن اطلاعات به داده
            current['رشد_قدرت_خریدار_درصد'] = growth
            current['قدرت_خریدار_اولیه'] = initial_power
            current['شیب'] = slope if slope is not None else 0

            # اعمال فیلتر بر اساس نوع
            if filter_type == 'positive_gentle':
                # رشد مثبت با شیب مثبت
                if growth > MIN_POSITIVE_GROWTH and (slope is None or slope >= 0):
                    filtered.append(current)

            elif filter_type == 'significant_upward':
                # رشد بیش از 10% با شیب مثبت
                if growth >= MIN_SIGNIFICANT_GROWTH * 100 and (slope is None or slope > 0):
                    filtered.append(current)

        # مرتب‌سازی بر اساس رشد (نزولی)
        filtered.sort(key=lambda x: x['رشد_قدرت_خریدار_درصد'], reverse=True)

        return filtered

    def get_filtered_summary(self) -> Dict[str, List[Dict]]:
        """
        دریافت خلاصه همه فیلترها

        Returns:
            دیکشنری شامل نتایج فیلترهای مختلف
        """
        if not self.all_symbols_cache:
            print("⚠️  ابتدا یک اسکن انجام دهید")
            return {}

        data = self.all_symbols_cache

        return {
            'positive_gentle': self.filter_with_slope(data, 'positive_gentle'),
            'significant_upward': self.filter_with_slope(data, 'significant_upward'),
            'all_growth': self.filter_by_growth(data)  # فیلتر قدیمی
        }
