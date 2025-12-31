"""
تنظیمات برنامه فیلتر نمادهای بورس
"""

import os
from dotenv import load_dotenv

load_dotenv()

# آدرس API های BrsApi.ir (رایگان بورس ایران)
BASE_URL = "https://BrsApi.ir/Api/Tsetmc"
ALL_SYMBOLS_URL = f"{BASE_URL}/AllSymbols.php"

# API Key (از فایل .env خوانده می‌شود)
BRSAPI_KEY = os.getenv('BRSAPI_KEY', '')

# تنظیمات زمانی
UPDATE_INTERVAL_MINUTES = 5  # هر 5 دقیقه یکبار

# تنظیمات Excel
EXCEL_OUTPUT_DIR = "output"
EXCEL_FILENAME_TEMPLATE = "bourse_data_{date}.xlsx"

# تنظیمات فیلتر
MIN_BUYER_POWER_GROWTH = 0.1  # حداقل 10% رشد قدرت خریدار نسبت به ابتدای روز

# هدرهای HTTP (برای جلوگیری از block شدن)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/106.0.0.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9'
}

