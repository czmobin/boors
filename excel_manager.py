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

        # مرتب‌سازی بر اساس قدرت خریدار (نزولی)
        if 'قدرت_خریدار' in df.columns:
            df = df.sort_values('قدرت_خریدار', ascending=False)
        elif 'buyer_power_ratio' in df.columns:
            df = df.sort_values('buyer_power_ratio', ascending=False)

        try:
            # بررسی اینکه آیا فایل از قبل وجود دارد
            if os.path.exists(self.filename):
                # خواندن داده‌های قبلی
                with pd.ExcelFile(self.filename) as xls:
                    existing_sheets = xls.sheet_names

                # نام شیت جدید بر اساس زمان
                sheet_name = datetime.now().strftime('%H-%M')

                # ذخیره در شیت جدید
                with pd.ExcelWriter(self.filename, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False, engine='openpyxl')

                print(f"داده‌ها در شیت {sheet_name} ذخیره شد")
            else:
                # ایجاد فایل جدید
                sheet_name = datetime.now().strftime('%H-%M')
                with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

                print(f"فایل جدید {self.filename} ایجاد شد")

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

            with pd.ExcelWriter(self.filename, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name='فیلتر_شده', index=False)

            print("شیت خلاصه نمادهای فیلتر شده ایجاد شد")
        except Exception as e:
            print(f"خطا در ایجاد شیت خلاصه: {e}")
