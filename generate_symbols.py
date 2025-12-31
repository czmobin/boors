#!/usr/bin/env python3
"""
ابزار ساخت فایل symbols.json از تمام نمادهای BrsApi
"""

import json
from brsapi_client import BrsApiClient


def generate_all_symbols():
    """دریافت همه نمادها و ساخت فایل symbols.json"""

    print("="*60)
    print("ساخت فایل symbols.json از BrsApi")
    print("="*60)

    # دریافت تمام نمادها
    client = BrsApiClient()
    all_data = client.get_all_symbols()

    if not all_data:
        print("❌ خطا در دریافت داده‌ها")
        return

    print(f"\n✅ {len(all_data)} نماد دریافت شد")

    # تبدیل به فرمت symbols.json
    symbols = []
    for item in all_data:
        symbol = {
            "name": item.get('l30', 'N/A'),
            "ticker": item.get('l18', 'N/A'),
            "id": item.get('id')
        }
        symbols.append(symbol)

    # ساخت فایل کامل
    output = {
        "_comment": "تمام نمادهای بورس ایران از BrsApi.ir",
        "_total": len(symbols),
        "symbols": symbols
    }

    # ذخیره در فایل
    with open('symbols_all.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ فایل symbols_all.json ساخته شد ({len(symbols)} نماد)")

    # ساخت فایل 100 نماد پرمعامله‌ترین
    # مرتب‌سازی بر اساس حجم معاملات
    top_symbols = sorted(
        [s for s in all_data if s.get('tvol', 0) > 0],
        key=lambda x: x.get('tvol', 0),
        reverse=True
    )[:100]

    top_100 = []
    for item in top_symbols:
        symbol = {
            "name": item.get('l30', 'N/A'),
            "ticker": item.get('l18', 'N/A'),
            "id": item.get('id'),
            "volume": item.get('tvol', 0)
        }
        top_100.append(symbol)

    output_top = {
        "_comment": "100 نماد پرمعامله بورس ایران",
        "_total": len(top_100),
        "symbols": top_100
    }

    with open('symbols_top100.json', 'w', encoding='utf-8') as f:
        json.dump(output_top, f, ensure_ascii=False, indent=2)

    print(f"✅ فایل symbols_top100.json ساخته شد ({len(top_100)} نماد)")

    # نمایش 10 نماد برتر
    print(f"\n{'='*60}")
    print("10 نماد پرمعامله‌ترین:")
    print(f"{'='*60}")

    for i, symbol in enumerate(top_100[:10], 1):
        print(f"{i:2d}. {symbol['ticker']:10s} - {symbol['name']}")
        print(f"     حجم: {symbol['volume']:,}")

    print(f"\n{'='*60}")
    print("فایل‌های ایجاد شده:")
    print(f"{'='*60}")
    print("1. symbols_all.json     - تمام 1369 نماد")
    print("2. symbols_top100.json  - 100 نماد برتر")
    print("\nبرای استفاده:")
    print("  cp symbols_top100.json symbols.json")
    print("  یا")
    print("  cp symbols_all.json symbols.json")


def filter_symbols_by_category():
    """فیلتر نمادها بر اساس دسته‌بندی"""

    client = BrsApiClient()
    all_data = client.get_all_symbols()

    if not all_data:
        return

    # گروه‌بندی بر اساس نوع بازار
    categories = {}
    for item in all_data:
        cat = item.get('cs', 'نامشخص')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "name": item.get('l30', 'N/A'),
            "ticker": item.get('l18', 'N/A'),
            "id": item.get('id')
        })

    print(f"\n{'='*60}")
    print("دسته‌بندی نمادها:")
    print(f"{'='*60}")

    for cat, symbols in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{cat}: {len(symbols)} نماد")

        # ذخیره هر دسته در فایل جداگانه
        if len(symbols) > 5:
            safe_name = cat.replace(' ', '_').replace('/', '_')
            filename = f"symbols_{safe_name}.json"

            output = {
                "_comment": f"نمادهای {cat}",
                "_total": len(symbols),
                "symbols": symbols
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

            print(f"  ✅ {filename}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--category':
        filter_symbols_by_category()
    else:
        generate_all_symbols()
