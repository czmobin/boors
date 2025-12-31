#!/usr/bin/env python3
"""
اسکریپت تست API بورس ایران (brsapi.ir)
"""

import json
from brsapi_client import BrsApiClient


def main():
    """تست اتصال به brsapi.ir و نمایش فرمت داده"""

    print("="*60)
    print("تست API بورس ایران (brsapi.ir)")
    print("="*60)
    print()

    # ایجاد کلاینت
    client = BrsApiClient()

    # تست اتصال
    if not client.test_connection():
        print("\n❌ اتصال ناموفق بود")
        print("\nلطفا بررسی کنید:")
        print("1. فایل .env ساخته شده و BRSAPI_KEY در آن تنظیم شده باشد")
        print("2. API Key معتبر باشد")
        print("3. اتصال اینترنت فعال باشد")
        return

    print("\n" + "="*60)
    print("دریافت اطلاعات کامل...")
    print("="*60)

    # دریافت تمام نمادها
    all_data = client.get_all_symbols()

    if not all_data:
        print("❌ خطا در دریافت داده")
        return

    print(f"\n✅ {len(all_data)} نماد دریافت شد\n")

    # نمایش اطلاعات کامل اولین نماد
    if all_data:
        first_symbol = all_data[0]

        print("="*60)
        print("اطلاعات کامل اولین نماد:")
        print("="*60)
        print(json.dumps(first_symbol, indent=2, ensure_ascii=False))

        # ذخیره نمونه در فایل
        with open('brsapi_sample.json', 'w', encoding='utf-8') as f:
            json.dump({
                'total_symbols': len(all_data),
                'first_symbol': first_symbol,
                'all_keys': list(first_symbol.keys())
            }, f, indent=2, ensure_ascii=False)

        print(f"\n✅ نمونه داده در فایل 'brsapi_sample.json' ذخیره شد")

        # جستجوی فیلدهای حقیقی/حقوقی
        print("\n" + "="*60)
        print("جستجوی فیلدهای حقیقی/حقوقی:")
        print("="*60)

        legal_fields = []
        for key in first_symbol.keys():
            key_lower = key.lower()
            if any(word in key_lower for word in ['legal', 'buy', 'sell', 'volume', 'count', 'client']):
                value = first_symbol.get(key)
                legal_fields.append((key, value))
                print(f"  {key}: {value}")

        if not legal_fields:
            print("  ⚠️  فیلد حقیقی/حقوقی یافت نشد")
            print("  📋 لیست تمام فیلدها:")
            for key in first_symbol.keys():
                print(f"    - {key}")

    # تست جستجوی نماد خاص (اگر symbols.json موجود باشد)
    try:
        import json as js
        with open('symbols.json', 'r', encoding='utf-8') as f:
            symbols_config = js.load(f)
            symbols = symbols_config.get('symbols', [])

            if symbols:
                test_symbol = symbols[0]
                ins_code = test_symbol.get('insCode')
                name = test_symbol.get('name')

                print(f"\n{'='*60}")
                print(f"تست جستجوی نماد: {name}")
                print(f"{'='*60}")

                symbol_data = client.get_symbol_data(ins_code, all_data)

                if symbol_data:
                    print(f"✅ نماد یافت شد:")
                    print(f"  نام: {symbol_data.get('lVal30', 'N/A')}")
                    print(f"  نماد: {symbol_data.get('lVal18', 'N/A')}")
                    print(f"  کد: {symbol_data.get('insCode', 'N/A')}")
                else:
                    print(f"❌ نماد با کد {ins_code} یافت نشد")

    except FileNotFoundError:
        print("\n⚠️  فایل symbols.json یافت نشد - تست جستجوی نماد انجام نشد")
    except Exception as e:
        print(f"\n⚠️  خطا در تست جستجوی نماد: {e}")


if __name__ == '__main__':
    main()
