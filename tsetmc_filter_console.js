/**
 * 🎯 فیلتر حرفه‌ای بورس ایران - نسخه Console
 *
 * نحوه استفاده:
 * 1. به سایت www.tsetmc.com بروید
 * 2. F12 را بزنید (Developer Tools)
 * 3. تب Console را انتخاب کنید
 * 4. این کد را کپی-پیست کنید و Enter بزنید
 * 5. دکمه 🔍 در گوشه پایین-راست ظاهر می‌شود
 */

(function() {
    'use strict';

    console.log('%c🎯 فیلتر حرفه‌ای بورس در حال بارگذاری...', 'color: #667eea; font-size: 16px; font-weight: bold;');

    // بررسی اینکه قبلاً اجرا نشده باشد
    if (window.BourseFilterInstalled) {
        console.log('%c⚠️ فیلتر بورس قبلاً نصب شده است!', 'color: orange; font-size: 14px;');
        return;
    }
    window.BourseFilterInstalled = true;

    // اضافه کردن استایل‌ها
    const style = document.createElement('style');
    style.textContent = `
        #bourse-filter-panel {
            position: fixed;
            top: 50px;
            right: 20px;
            width: 420px;
            max-height: 85vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            z-index: 999999;
            overflow: hidden;
            font-family: Tahoma, Arial, sans-serif;
            display: none;
        }

        #bourse-filter-panel.active {
            display: block;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from { transform: translateX(450px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        .bfilter-header {
            background: rgba(0,0,0,0.2);
            padding: 15px 20px;
            color: white;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .bfilter-close {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }

        .bfilter-close:hover {
            background: rgba(255,255,255,0.3);
            transform: rotate(90deg);
        }

        .bfilter-body {
            padding: 20px;
            max-height: calc(85vh - 140px);
            overflow-y: auto;
            background: white;
        }

        .bfilter-body::-webkit-scrollbar { width: 8px; }
        .bfilter-body::-webkit-scrollbar-track { background: #f1f1f1; }
        .bfilter-body::-webkit-scrollbar-thumb { background: #667eea; border-radius: 4px; }

        .bfilter-option {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 14px;
            margin-bottom: 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }

        .bfilter-option:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            border-color: #667eea;
        }

        .bfilter-option-title {
            font-weight: bold;
            color: #2d3748;
            font-size: 15px;
            margin-bottom: 5px;
        }

        .bfilter-option-desc {
            font-size: 12px;
            color: #4a5568;
        }

        .bfilter-footer {
            padding: 15px;
            background: rgba(0,0,0,0.05);
            display: flex;
            gap: 10px;
        }

        .bfilter-btn {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            font-size: 14px;
        }

        .bfilter-btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .bfilter-btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .bfilter-btn-secondary {
            background: #e2e8f0;
            color: #2d3748;
        }

        .bfilter-btn-secondary:hover { background: #cbd5e0; }

        #bfilter-toggle-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 65px;
            height: 65px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            font-size: 32px;
            cursor: pointer;
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.5);
            z-index: 999998;
            transition: all 0.3s;
        }

        #bfilter-toggle-btn:hover {
            transform: scale(1.1) rotate(90deg);
            box-shadow: 0 8px 30px rgba(102, 126, 234, 0.7);
        }

        .bresults-panel {
            margin-top: 15px;
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            max-height: 320px;
            overflow-y: auto;
        }

        .bresult-item {
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 6px;
            border-right: 4px solid #667eea;
            font-size: 12px;
            transition: all 0.2s;
        }

        .bresult-item:hover {
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            transform: translateX(-3px);
        }

        .bresult-symbol {
            font-weight: bold;
            color: #667eea;
            font-size: 15px;
            margin-bottom: 6px;
        }

        .bresult-detail {
            color: #4a5568;
            margin: 3px 0;
            font-size: 12px;
        }

        .bloading {
            text-align: center;
            padding: 25px;
            color: #667eea;
            font-size: 15px;
        }

        .bloading:after {
            content: '...';
            animation: dots 1.5s infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        .bcustom-input {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            margin-top: 8px;
            font-size: 13px;
            transition: all 0.3s;
        }

        .bcustom-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .bstats {
            background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%);
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 12px;
            font-size: 12px;
            color: #2d3748;
        }
    `;
    document.head.appendChild(style);

    // ساخت UI
    function createUI() {
        // دکمه شناور
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'bfilter-toggle-btn';
        toggleBtn.innerHTML = '🔍';
        toggleBtn.title = 'فیلتر حرفه‌ای بورس';
        document.body.appendChild(toggleBtn);

        // پنل فیلتر
        const panel = document.createElement('div');
        panel.id = 'bourse-filter-panel';
        panel.innerHTML = `
            <div class="bfilter-header">
                <span>🎯 فیلتر حرفه‌ای بورس</span>
                <button class="bfilter-close">×</button>
            </div>
            <div class="bfilter-body">
                <div class="bfilter-option" data-filter="money_flow">
                    <div class="bfilter-option-title">💰 ورود پول حقیقی</div>
                    <div class="bfilter-option-desc">نمادهای با ورود پول بالا (حجم × قیمت)</div>
                </div>

                <div class="bfilter-option" data-filter="buying_power">
                    <div class="bfilter-option-title">📈 قدرت خرید</div>
                    <div class="bfilter-option-desc">نمادهای با حجم و رشد قیمت مثبت</div>
                </div>

                <div class="bfilter-option" data-filter="high_volume">
                    <div class="bfilter-option-title">📊 حجم بالا</div>
                    <div class="bfilter-option-desc">حجم بیشتر از 2 برابر میانگین بازار</div>
                </div>

                <div class="bfilter-option" data-filter="price_increase">
                    <div class="bfilter-option-title">🚀 رشد قیمت قوی</div>
                    <div class="bfilter-option-desc">رشد قیمت بالای 2 درصد</div>
                </div>

                <div class="bfilter-option" data-filter="price_decrease">
                    <div class="bfilter-option-title">📉 افت قیمت</div>
                    <div class="bfilter-option-desc">افت قیمت بیش از 2 درصد</div>
                </div>

                <div class="bfilter-option" data-filter="smart_money">
                    <div class="bfilter-option-title">🧠 پول هوشمند</div>
                    <div class="bfilter-option-desc">حجم بالا + رشد قیمت قوی</div>
                </div>

                <div class="bfilter-option" data-filter="positive_all">
                    <div class="bfilter-option-title">✅ همه مثبت</div>
                    <div class="bfilter-option-desc">قیمت، حجم، و ارزش همگی مثبت</div>
                </div>

                <div class="bfilter-option" data-filter="queue_buy">
                    <div class="bfilter-option-title">🔥 صف خرید</div>
                    <div class="bfilter-option-desc">نمادهایی که در حداکثر قیمت روزانه هستند</div>
                </div>

                <div class="bfilter-option" data-filter="high_value">
                    <div class="bfilter-option-title">💎 ارزش معاملات بالا</div>
                    <div class="bfilter-option-desc">بیش از 10 میلیارد تومان ارزش معاملات</div>
                </div>

                <div class="bfilter-option" data-filter="active_trading">
                    <div class="bfilter-option-title">⚡ معاملات فعال</div>
                    <div class="bfilter-option-desc">تعداد معاملات بالای 500</div>
                </div>

                <div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #e2e8f0;">
                    <div class="bfilter-option-title" style="margin-bottom: 10px;">⚙️ فیلتر سفارشی</div>
                    <select class="bcustom-input" id="bcustom-type">
                        <option value="">-- نوع فیلتر --</option>
                        <option value="price_change">تغییر قیمت (درصد)</option>
                        <option value="volume">حجم (حداقل)</option>
                        <option value="value">ارزش (میلیارد تومان)</option>
                        <option value="count">تعداد معاملات</option>
                    </select>
                    <input type="number" class="bcustom-input" id="bcustom-threshold" placeholder="آستانه (مثلاً: 2 برای 2%)">
                </div>

                <div id="bfilter-results"></div>
            </div>
            <div class="bfilter-footer">
                <button class="bfilter-btn bfilter-btn-secondary" id="bclear-btn">پاک کردن</button>
                <button class="bfilter-btn bfilter-btn-primary" id="bapply-custom">اعمال سفارشی</button>
            </div>
        `;
        document.body.appendChild(panel);

        // رویدادها
        toggleBtn.onclick = () => panel.classList.toggle('active');
        panel.querySelector('.bfilter-close').onclick = () => panel.classList.remove('active');

        document.querySelectorAll('.bfilter-option').forEach(option => {
            option.onclick = function() {
                const filterType = this.getAttribute('data-filter');
                if (filterType) applyFilter(filterType);
            };
        });

        document.getElementById('bclear-btn').onclick = () => {
            document.getElementById('bfilter-results').innerHTML = '';
        };

        document.getElementById('bapply-custom').onclick = applyCustomFilter;
    }

    // دریافت داده‌های بازار
    async function getMarketData() {
        try {
            const response = await fetch('http://www.tsetmc.com/tsev2/data/MarketWatchPlus.aspx');
            const text = await response.text();
            const lines = text.trim().split('\n');
            const stocks = [];

            for (let line of lines) {
                if (!line) continue;
                const parts = line.split(',');
                if (parts.length < 15) continue;

                try {
                    const yesterdayPrice = parseFloat(parts[9]) || 0;
                    const lastPrice = parseFloat(parts[6]) || 0;

                    const stock = {
                        insCode: parts[0],
                        symbol: parts[2],
                        name: parts[3],
                        lastPrice: lastPrice,
                        closePrice: parseFloat(parts[7]) || 0,
                        firstPrice: parseFloat(parts[8]) || 0,
                        yesterdayPrice: yesterdayPrice,
                        volume: parseFloat(parts[10]) || 0,
                        value: parseFloat(parts[11]) || 0,
                        low: parseFloat(parts[12]) || 0,
                        high: parseFloat(parts[13]) || 0,
                        count: parseFloat(parts[14]) || 0,
                        priceChange: yesterdayPrice > 0 ? ((lastPrice - yesterdayPrice) / yesterdayPrice) * 100 : 0
                    };

                    stocks.push(stock);
                } catch (e) {
                    continue;
                }
            }

            return stocks;
        } catch (error) {
            console.error('خطا در دریافت داده‌ها:', error);
            return [];
        }
    }

    // اعمال فیلتر
    async function applyFilter(filterType) {
        const resultsDiv = document.getElementById('bfilter-results');
        resultsDiv.innerHTML = '<div class="bloading">در حال بارگذاری داده‌ها از TSETMC</div>';

        const stocks = await getMarketData();

        if (stocks.length === 0) {
            resultsDiv.innerHTML = '<div style="text-align:center;color:#e53e3e;padding:20px;">❌ خطا در دریافت داده‌ها</div>';
            return;
        }

        let filtered = [];
        const avgVolume = stocks.reduce((sum, s) => sum + s.volume, 0) / stocks.length;

        switch (filterType) {
            case 'money_flow':
                filtered = stocks.filter(s => s.volume > 500000 && s.priceChange > 1);
                filtered.sort((a, b) => (b.volume * b.lastPrice) - (a.volume * a.lastPrice));
                break;

            case 'buying_power':
                filtered = stocks.filter(s => s.volume > 300000 && s.priceChange > 0.5);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'high_volume':
                filtered = stocks.filter(s => s.volume > avgVolume * 2);
                filtered.sort((a, b) => b.volume - a.volume);
                break;

            case 'price_increase':
                filtered = stocks.filter(s => s.priceChange > 2);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'price_decrease':
                filtered = stocks.filter(s => s.priceChange < -2);
                filtered.sort((a, b) => a.priceChange - b.priceChange);
                break;

            case 'smart_money':
                filtered = stocks.filter(s => s.volume > 800000 && s.priceChange > 1.5);
                filtered.sort((a, b) => (b.volume * b.priceChange) - (a.volume * a.priceChange));
                break;

            case 'positive_all':
                filtered = stocks.filter(s => s.priceChange > 0 && s.volume > 100000 && s.value > 1000000000);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'queue_buy':
                filtered = stocks.filter(s => Math.abs(s.lastPrice - s.high) < 10 && s.priceChange > 3 && s.volume > 200000);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'high_value':
                filtered = stocks.filter(s => s.value > 10000000000);
                filtered.sort((a, b) => b.value - a.value);
                break;

            case 'active_trading':
                filtered = stocks.filter(s => s.count > 500);
                filtered.sort((a, b) => b.count - a.count);
                break;
        }

        const filterNames = {
            'money_flow': 'ورود پول حقیقی',
            'buying_power': 'قدرت خرید',
            'high_volume': 'حجم بالا',
            'price_increase': 'رشد قیمت',
            'price_decrease': 'افت قیمت',
            'smart_money': 'پول هوشمند',
            'positive_all': 'همه مثبت',
            'queue_buy': 'صف خرید',
            'high_value': 'ارزش بالا',
            'active_trading': 'معاملات فعال'
        };

        displayResults(filtered.slice(0, 25), filterNames[filterType] || filterType, stocks.length);
    }

    // اعمال فیلتر سفارشی
    async function applyCustomFilter() {
        const threshold = parseFloat(document.getElementById('bcustom-threshold').value);
        const type = document.getElementById('bcustom-type').value;

        if (!threshold || !type) {
            alert('⚠️ لطفاً نوع فیلتر و آستانه را مشخص کنید');
            return;
        }

        const resultsDiv = document.getElementById('bfilter-results');
        resultsDiv.innerHTML = '<div class="bloading">در حال بارگذاری داده‌ها</div>';

        const stocks = await getMarketData();
        let filtered = [];

        switch (type) {
            case 'price_change':
                filtered = stocks.filter(s => s.priceChange > threshold);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'volume':
                filtered = stocks.filter(s => s.volume > threshold);
                filtered.sort((a, b) => b.volume - a.volume);
                break;

            case 'value':
                filtered = stocks.filter(s => s.value > threshold * 1000000000);
                filtered.sort((a, b) => b.value - a.value);
                break;

            case 'count':
                filtered = stocks.filter(s => s.count > threshold);
                filtered.sort((a, b) => b.count - a.count);
                break;
        }

        displayResults(filtered.slice(0, 25), `فیلتر سفارشی (${type})`, stocks.length);
    }

    // نمایش نتایج
    function displayResults(stocks, filterName, totalStocks) {
        const resultsDiv = document.getElementById('bfilter-results');

        if (stocks.length === 0) {
            resultsDiv.innerHTML = '<div style="text-align:center;color:#718096;padding:20px;">❌ نمادی یافت نشد</div>';
            return;
        }

        let html = '<div class="bresults-panel">';
        html += `<div class="bstats">
            <strong>📊 ${filterName}</strong><br>
            یافت شده: ${stocks.length} نماد از ${totalStocks} نماد کل بازار
        </div>`;

        stocks.forEach((stock, index) => {
            const changeColor = stock.priceChange >= 0 ? '#48bb78' : '#f56565';
            const changeIcon = stock.priceChange >= 0 ? '📈' : '📉';

            html += `
                <div class="bresult-item">
                    <div class="bresult-symbol">${index + 1}. ${stock.symbol} ${changeIcon}</div>
                    <div class="bresult-detail">💵 قیمت: ${stock.lastPrice.toLocaleString()} ریال</div>
                    <div class="bresult-detail" style="color:${changeColor};font-weight:bold;">
                        ${changeIcon} تغییر: ${stock.priceChange.toFixed(2)}%
                    </div>
                    <div class="bresult-detail">📦 حجم: ${stock.volume.toLocaleString()}</div>
                    <div class="bresult-detail">💰 ارزش: ${(stock.value / 1000000000).toFixed(2)} میلیارد</div>
                    <div class="bresult-detail">🔢 تعداد: ${stock.count.toLocaleString()} معامله</div>
                </div>
            `;
        });

        html += '</div>';
        resultsDiv.innerHTML = html;
    }

    // اجرا
    createUI();
    console.log('%c✅ فیلتر حرفه‌ای بورس آماده است!', 'color: #48bb78; font-size: 16px; font-weight: bold;');
    console.log('%c🔍 دکمه فیلتر در گوشه پایین-راست صفحه ظاهر شده است', 'color: #667eea; font-size: 14px;');

})();
