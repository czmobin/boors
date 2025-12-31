#!/usr/bin/env python3
"""
ابزار کمکی برای یافتن insCode نمادها
"""

import requests
import sys


def search_symbol(symbol_name: str):
    """
    جستجوی نماد در TSETMC

    Args:
        symbol_name: نام یا نماد کوتاه
    """
    print(f"در حال جستجو برای: {symbol_name}")

    # این API جستجو در TSETMC است
    search_url = f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{symbol_name}"

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://tsetmc.com',
        'referer': 'https://tsetmc.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if 'instrumentSearch' in data:
            results = data['instrumentSearch']

            if not results:
                print(f"نمادی با نام '{symbol_name}' پیدا نشد")
                return

            print(f"\n{'='*80}")
            print(f"نتایج جستجو برای '{symbol_name}':")
            print(f"{'='*80}\n")

            for idx, item in enumerate(results[:10], 1):  # نمایش 10 نتیجه اول
                ins_code = item.get('insCode', 'N/A')
                ticker = item.get('lVal18', 'N/A')
                name = item.get('lVal30', 'N/A')

                print(f"{idx}. {ticker}")
                print(f"   نام کامل: {name}")
                print(f"   کد نماد: {ins_code}")
                print(f"   URL: https://tsetmc.com/instInfo/{ins_code}")
                print()

            # فرمت JSON برای کپی کردن
            if results:
                first = results[0]
                print(f"\n{'='*80}")
                print("فرمت JSON برای افزودن به symbols.json:")
                print(f"{'='*80}")
                print("{")
                print(f'  "name": "{first.get("lVal30", "")}",')
                print(f'  "insCode": "{first.get("insCode", "")}",')
                print(f'  "ticker": "{first.get("lVal18", "")}"')
                print("}")

        else:
            print("خطا در دریافت نتایج جستجو")

    except Exception as e:
        print(f"خطا در جستجو: {e}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("استفاده:")
        print("  python find_symbol.py <نام_نماد>")
        print("\nمثال:")
        print("  python find_symbol.py غدیر")
        print("  python find_symbol.py خودرو")
        sys.exit(1)

    symbol = ' '.join(sys.argv[1:])
    search_symbol(symbol)
