"""
کلاس برای دریافت داده از API های TSETMC
"""

import requests
import time
from typing import Dict, Optional
from config import INSTRUMENT_INFO_URL, CLIENT_TYPE_URL, HEADERS


class TSETMCClient:
    """کلاس برای ارتباط با API های TSETMC"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_instrument_info(self, ins_code: str, retries: int = 3) -> Optional[Dict]:
        """
        دریافت اطلاعات کلی نماد

        Args:
            ins_code: کد نماد
            retries: تعداد دفعات تلاش مجدد

        Returns:
            دیکشنری حاوی اطلاعات نماد یا None در صورت خطا
        """
        for attempt in range(retries):
            try:
                url = f"{INSTRUMENT_INFO_URL}/{ins_code}"
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                print(f"خطا در دریافت اطلاعات نماد {ins_code}: {e}")
                return None
        return None

    def get_client_type(self, ins_code: str, retries: int = 3) -> Optional[Dict]:
        """
        دریافت اطلاعات حقیقی و حقوقی

        Args:
            ins_code: کد نماد
            retries: تعداد دفعات تلاش مجدد

        Returns:
            دیکشنری حاوی اطلاعات خرید و فروش حقیقی/حقوقی یا None در صورت خطا
        """
        for attempt in range(retries):
            try:
                url = f"{CLIENT_TYPE_URL}/{ins_code}/1/0"
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                print(f"خطا در دریافت اطلاعات حقیقی/حقوقی نماد {ins_code}: {e}")
                return None
        return None

    def get_all_data(self, ins_code: str) -> Optional[Dict]:
        """
        دریافت تمام اطلاعات مورد نیاز یک نماد

        Args:
            ins_code: کد نماد

        Returns:
            دیکشنری حاوی هر دو نوع داده یا None در صورت خطا
        """
        instrument_info = self.get_instrument_info(ins_code)
        time.sleep(0.5)  # تاخیر برای جلوگیری از فشار زیاد به سرور
        client_type = self.get_client_type(ins_code)

        if instrument_info and client_type:
            return {
                'instrument_info': instrument_info,
                'client_type': client_type
            }
        return None
