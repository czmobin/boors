"""
تنظیمات برنامه فیلتر نمادهای بورس
"""

# آدرس API های TSETMC
BASE_URL = "https://cdn.tsetmc.com/api"
INSTRUMENT_INFO_URL = f"{BASE_URL}/Instrument/GetInstrumentInfo"
CLIENT_TYPE_URL = f"{BASE_URL}/ClientType/GetClientType"

# تنظیمات زمانی
UPDATE_INTERVAL_MINUTES = 5  # هر 5 دقیقه یکبار

# تنظیمات Excel
EXCEL_OUTPUT_DIR = "output"
EXCEL_FILENAME_TEMPLATE = "bourse_data_{date}.xlsx"

# تنظیمات فیلتر
MIN_BUYER_POWER_GROWTH = 0.1  # حداقل 10% رشد قدرت خریدار نسبت به ابتدای روز

# هدرهای HTTP
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'origin': 'https://tsetmc.com',
    'referer': 'https://tsetmc.com/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
}
