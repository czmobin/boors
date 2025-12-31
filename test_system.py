#!/usr/bin/env python3
"""
تست کامل سیستم فیلتر با BrsApi
"""

from stock_filter import StockFilter
from calculator import BourseCalculator


def test_calculator():
    """تست calculator با داده‌های BrsApi"""
    print("="*60)
    print("تست Calculator")
    print("="*60)

    # داده نمونه از BrsApi
    sample_data = {
        'Buy_CountI': 30070,
        'Buy_CountN': 71,
        'Sell_CountI': 13256,
        'Sell_CountN': 35,
        'Buy_I_Volume': 103358761,
        'Buy_N_Volume': 9356697,
        'Sell_I_Volume': 108742074,
        'Sell_N_Volume': 3973384
    }

    calc = BourseCalculator()
    result = calc.calculate_buyer_power(sample_data)

    print(f"✅ Calculator کار می‌کند:")
    print(f"  - قدرت خریدار: {result['buyer_power_ratio']}")
    print(f"  - ورود پول خالص: {result['net_money_flow']:,.0f} میلیون")
    print()


def test_stock_filter():
    """تست StockFilter"""
    print("="*60)
    print("تست Stock Filter")
    print("="*60)

    try:
        filter_system = StockFilter()

        print(f"✅ StockFilter ایجاد شد")
        print(f"  - تعداد نمادها: {len(filter_system.symbols)}")
        print()

        # تست دریافت داده
        print("تلاش برای دریافت داده از BrsApi...")
        data = filter_system.fetch_and_calculate()

        if data:
            print(f"\n✅ دریافت داده موفق:")
            print(f"  - تعداد نمادهای پردازش شده: {len(data)}")

            if data:
                first = data[0]
                print(f"\n📊 نمونه داده اولین نماد:")
                print(f"  - نماد: {first.get('نماد')}")
                print(f"  - نام: {first.get('نام_کامل')}")
                print(f"  - قدرت خریدار: {first.get('قدرت_خریدار')}")
                print(f"  - ورود پول: {first.get('ورود_پول_خالص_میلیون'):,.0f} میلیون")
        else:
            print("❌ دریافت داده ناموفق بود")
            print("   احتمالا API Key تنظیم نشده است")

    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "="*60)
    print("تست سیستم کامل با BrsApi.ir")
    print("="*60 + "\n")

    # Test 1: Calculator
    test_calculator()

    # Test 2: Stock Filter
    test_stock_filter()

    print("\n" + "="*60)
    print("تست به پایان رسید")
    print("="*60)


if __name__ == '__main__':
    main()
