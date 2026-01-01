"""
مدیریت ذخیره داده در Excel
"""

import pandas as pd
import os
from datetime import datetime
from typing import List, Dict
from config import EXCEL_OUTPUT_DIR, EXCEL_FILENAME_TEMPLATE


class ExcelManager:
    """کلاس برای مدیریت ذخیره و بارگذاری داده‌ها در Excel"""

    def __init__(self):
        # ایجاد پوشه خروجی در صورت عدم وجود
        if not os.path.exists(EXCEL_OUTPUT_DIR):
            os.makedirs(EXCEL_OUTPUT_DIR)

        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.filename = os.path.join(
            EXCEL_OUTPUT_DIR,
            EXCEL_FILENAME_TEMPLATE.format(date=self.current_date)
        )

    def save_data(self, data_list: List[Dict]) -> None:
        """
        ذخیره داده‌ها در Excel

        Args:
            data_list: لیستی از دیکشنری‌های حاوی داده‌های نمادها
        """
        if not data_list:
            print("هیچ داده‌ای برای ذخیره وجود ندارد")
            return

        # تبدیل به DataFrame
        df = pd.DataFrame(data_list)

        # تعیین ترتیب ستون‌ها (ثابت برای جلوگیری از قاطی شدن)
        column_order = [
            'نماد', 'کد', 'زمان', 'قیمت_پایانی', 'درصد_تغییر',
            'حجم_معاملات', 'ارزش_معاملات',
            'حجم_خرید_حقیقی', 'تعداد_خرید_حقیقی', 'حجم_فروش_حقیقی', 'تعداد_فروش_حقیقی',
            'حجم_خرید_حقوقی', 'حجم_فروش_حقوقی', 'تعداد_خرید_حقوقی', 'تعداد_فروش_حقوقی',
            'X_سرانه_خرید_حقیقی_تومان', 'Y_سرانه_فروش_حقیقی_تومان', 'تفاضل_سرانه_تومان', 'قدرت_خریدار',
            'ورود_پول_حقوقی_میلیون', 'ورود_پول_حقیقی_میلیون',
            'سرانه_خرید_حقوقی_میلیون', 'سرانه_فروش_حقوقی_میلیون', 'ورود_پول_خالص_میلیون'
        ]

        # فقط ستون‌هایی که موجودند رو استفاده کن
        available_columns = [col for col in column_order if col in df.columns]
        df = df[available_columns]

        # مرتب‌سازی بر اساس قدرت خریدار (نزولی)
        if 'قدرت_خریدار' in df.columns:
            df = df.sort_values('قدرت_خریدار', ascending=False)
        elif 'buyer_power_ratio' in df.columns:
            df = df.sort_values('buyer_power_ratio', ascending=False)

        try:
            # نام شیت بر اساس زمان
            sheet_name = datetime.now().strftime('%H-%M')

            # همیشه فایل رو از نو بساز (فقط آخرین اسکن نگه داشته میشه)
            with pd.ExcelWriter(self.filename, mode='w', engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

            print(f"✅ داده‌ها در شیت {sheet_name} ذخیره شد (فایل از نو ساخته شد)")

        except Exception as e:
            print(f"خطا در ذخیره داده‌ها: {e}")

    def load_first_data(self) -> pd.DataFrame:
        """
        بارگذاری اولین داده‌های روز (برای مقایسه)

        Returns:
            DataFrame حاوی اولین داده‌های روز یا None
        """
        try:
            if os.path.exists(self.filename):
                with pd.ExcelFile(self.filename) as xls:
                    # خواندن اولین شیت
                    first_sheet = xls.sheet_names[0]
                    df = pd.read_excel(xls, sheet_name=first_sheet)
                    return df
            return None
        except Exception as e:
            print(f"خطا در بارگذاری داده‌های اولیه: {e}")
            return None

    def create_summary_sheet(self, filtered_data: List[Dict]) -> None:
        """
        ایجاد شیت خلاصه برای نمادهای فیلتر شده

        Args:
            filtered_data: لیست نمادهای فیلتر شده
        """
        if not filtered_data:
            return

        try:
            df = pd.DataFrame(filtered_data)

            # اگر فایل وجود داره، شیت فیلتر شده رو اضافه کن
            if os.path.exists(self.filename):
                with pd.ExcelWriter(self.filename, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                    df.to_excel(writer, sheet_name='فیلتر_شده', index=False)
                print("✅ شیت 'فیلتر_شده' اضافه شد")
            else:
                print("⚠️ فایل Excel موجود نیست - ابتدا اسکن کنید")
        except Exception as e:
            print(f"خطا در ایجاد شیت خلاصه: {e}")
