"""
کلاس برای دریافت داده از API بورس ایران (brsapi.ir)
"""

import requests
import time
from typing import Dict, List, Optional
from config import ALL_SYMBOLS_URL, BRSAPI_KEY, HEADERS


class BrsApiClient:
    """کلاس برای ارتباط با API بورس ایران (brsapi.ir)"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.api_key = BRSAPI_KEY

        if not self.api_key:
            print("⚠️  هشدار: API Key یافت نشد!")
            print("لطفا BRSAPI_KEY را در فایل .env تنظیم کنید")
            print("برای دریافت API Key رایگان به https://brsapi.ir بروید")

    def get_all_symbols(self, retries: int = 3, date: str = None) -> Optional[List[Dict]]:
        """
        دریافت اطلاعات تمام نمادها از brsapi.ir

        این API یک بار فراخوانی می‌شود و اطلاعات کامل تمام نمادها را برمی‌گرداند
        شامل: قیمت، حجم، ورود/خروج پول، حقیقی/حقوقی و ...

        Args:
            retries: تعداد دفعات تلاش مجدد
            date: تاریخ به فرمت YYYY-MM-DD (اختیاری - برای داده‌های تاریخی)

        Returns:
            لیست دیکشنری حاوی اطلاعات نمادها یا None در صورت خطا
        """
        if not self.api_key:
            print("❌ API Key تنظیم نشده است")
            return None

        for attempt in range(retries):
            try:
                url = f"{ALL_SYMBOLS_URL}?key={self.api_key}"
                if date:
                    url += f"&date={date}"
                    print(f"📅 در حال دریافت داده‌های تاریخ {date}...")

                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                data = response.json()

                # بررسی ساختار پاسخ
                if isinstance(data, list):
                    date_info = f" (تاریخ: {date})" if date else ""
                    print(f"✅ {len(data)} نماد از brsapi.ir دریافت شد{date_info}")
                    return data
                else:
                    print(f"⚠️  فرمت داده غیرمنتظره: {type(data)}")
                    return None

            except requests.exceptions.Timeout:
                print(f"⏱️  Timeout در تلاش {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print("❌ خطای 403: API Key نامعتبر است")
                    print("لطفا API Key خود را در https://brsapi.ir بررسی کنید")
                    return None
                elif e.response.status_code == 429:
                    print("⚠️  محدودیت تعداد درخواست - کمی صبر کنید")
                    time.sleep(5)
                    if attempt < retries - 1:
                        continue
                else:
                    print(f"❌ خطای HTTP {e.response.status_code}: {e}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue

            except Exception as e:
                print(f"❌ خطا در تلاش {attempt + 1}/{retries}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue

        return None

    def get_symbol_data(self, ins_code: str, all_data: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        استخراج اطلاعات یک نماد خاص از داده‌های دریافتی

        Args:
            ins_code: کد نماد
            all_data: داده‌های تمام نمادها (اگر قبلا دریافت شده باشد)

        Returns:
            دیکشنری حاوی اطلاعات نماد یا None در صورت عدم یافتن
        """
        if all_data is None:
            all_data = self.get_all_symbols()

        if not all_data:
            return None

        # جستجوی نماد با insCode
        for symbol in all_data:
            # بررسی فیلدهای مختلف که ممکن است insCode داشته باشند
            symbol_code = symbol.get('insCode') or symbol.get('InstrumentID') or symbol.get('instCode')

            if symbol_code and str(symbol_code) == str(ins_code):
                return symbol

        print(f"⚠️  نماد با کد {ins_code} یافت نشد")
        return None

    def test_connection(self) -> bool:
        """
        تست اتصال به API

        Returns:
            True اگر اتصال موفق باشد
        """
        print("🔍 در حال تست اتصال به brsapi.ir...")

        data = self.get_all_symbols()

        if data and len(data) > 0:
            print(f"✅ اتصال موفق - {len(data)} نماد دریافت شد")

            # نمایش نمونه اطلاعات اولین نماد
            first_symbol = data[0]
            print(f"\nنمونه داده (اولین نماد):")
            print(f"  نام: {first_symbol.get('lVal30', 'N/A')}")
            print(f"  نماد: {first_symbol.get('lVal18', 'N/A')}")
            print(f"  کد: {first_symbol.get('insCode', 'N/A')}")

            # نمایش کلیدهای موجود
            print(f"\n📊 فیلدهای موجود در API ({len(first_symbol)} فیلد):")
            for key in list(first_symbol.keys())[:10]:
                print(f"  - {key}")
            if len(first_symbol) > 10:
                print(f"  ... و {len(first_symbol) - 10} فیلد دیگر")

            return True
        else:
            print("❌ خطا در دریافت داده")
            return False
