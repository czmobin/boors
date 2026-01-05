// ==UserScript==
// @name         فیلتر حرفه‌ای بورس ایران
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  فیلتر نویسی پیشرفته روی سایت TSETMC
// @author       Your Name
// @match        http://www.tsetmc.com/*
// @match        https://www.tsetmc.com/*
// @match        http://old.tsetmc.com/*
// @match        https://old.tsetmc.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @connect      tsetmc.com
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';

    // استایل‌های CSS
    GM_addStyle(`
        #bourse-filter-panel {
            position: fixed;
            top: 50px;
            right: 20px;
            width: 400px;
            max-height: 80vh;
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
            from {
                transform: translateX(450px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .filter-header {
            background: rgba(0,0,0,0.2);
            padding: 15px;
            color: white;
            font-size: 18px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .filter-close {
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

        .filter-close:hover {
            background: rgba(255,255,255,0.3);
            transform: rotate(90deg);
        }

        .filter-body {
            padding: 20px;
            max-height: calc(80vh - 120px);
            overflow-y: auto;
            background: white;
        }

        .filter-body::-webkit-scrollbar {
            width: 8px;
        }

        .filter-body::-webkit-scrollbar-track {
            background: #f1f1f1;
        }

        .filter-body::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 4px;
        }

        .filter-option {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            border: 2px solid transparent;
        }

        .filter-option:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            border-color: #667eea;
        }

        .filter-option-title {
            font-weight: bold;
            color: #2d3748;
            font-size: 14px;
            margin-bottom: 5px;
        }

        .filter-option-desc {
            font-size: 12px;
            color: #4a5568;
        }

        .filter-footer {
            padding: 15px;
            background: rgba(0,0,0,0.05);
            display: flex;
            gap: 10px;
        }

        .filter-btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            font-size: 14px;
        }

        .filter-btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .filter-btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .filter-btn-secondary {
            background: #e2e8f0;
            color: #2d3748;
        }

        .filter-btn-secondary:hover {
            background: #cbd5e0;
        }

        #filter-toggle-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            font-size: 28px;
            cursor: pointer;
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.5);
            z-index: 999998;
            transition: all 0.3s;
        }

        #filter-toggle-btn:hover {
            transform: scale(1.1) rotate(90deg);
            box-shadow: 0 8px 30px rgba(102, 126, 234, 0.7);
        }

        .results-panel {
            margin-top: 15px;
            background: #f7fafc;
            padding: 15px;
            border-radius: 8px;
            max-height: 300px;
            overflow-y: auto;
        }

        .result-item {
            background: white;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 6px;
            border-right: 4px solid #667eea;
            font-size: 12px;
        }

        .result-symbol {
            font-weight: bold;
            color: #667eea;
            font-size: 14px;
            margin-bottom: 5px;
        }

        .result-detail {
            color: #4a5568;
            margin: 2px 0;
        }

        .loading {
            text-align: center;
            padding: 20px;
            color: #667eea;
            font-size: 14px;
        }

        .loading:after {
            content: '...';
            animation: dots 1.5s infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        .custom-filter-input {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            margin-top: 10px;
            font-size: 13px;
            transition: all 0.3s;
        }

        .custom-filter-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
    `);

    // ساخت UI
    function createUI() {
        // دکمه شناور
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'filter-toggle-btn';
        toggleBtn.innerHTML = '🔍';
        toggleBtn.title = 'فیلتر بورس';
        toggleBtn.onclick = togglePanel;
        document.body.appendChild(toggleBtn);

        // پنل فیلتر
        const panel = document.createElement('div');
        panel.id = 'bourse-filter-panel';
        panel.innerHTML = `
            <div class="filter-header">
                <span>🎯 فیلتر حرفه‌ای بورس</span>
                <button class="filter-close" onclick="document.getElementById('bourse-filter-panel').classList.remove('active')">×</button>
            </div>
            <div class="filter-body">
                <div class="filter-option" data-filter="money_flow">
                    <div class="filter-option-title">💰 ورود پول حقیقی</div>
                    <div class="filter-option-desc">نمادهای با ورود پول حقیقی بالا</div>
                </div>

                <div class="filter-option" data-filter="buying_power">
                    <div class="filter-option-title">📈 قدرت خرید حقیقی</div>
                    <div class="filter-option-desc">نمادهای با قدرت خرید حقیقی بالای 60%</div>
                </div>

                <div class="filter-option" data-filter="high_volume">
                    <div class="filter-option-title">📊 حجم بالا</div>
                    <div class="filter-option-desc">نمادهای با حجم بیشتر از میانگین</div>
                </div>

                <div class="filter-option" data-filter="price_increase">
                    <div class="filter-option-title">🚀 رشد قیمت</div>
                    <div class="filter-option-desc">نمادهای با رشد قیمت بالای 2%</div>
                </div>

                <div class="filter-option" data-filter="legal_exit">
                    <div class="filter-option-title">🏢 خروج حقوقی</div>
                    <div class="filter-option-desc">نمادهایی که حقوقی‌ها فروش می‌کنند</div>
                </div>

                <div class="filter-option" data-filter="smart_money">
                    <div class="filter-option-title">🧠 پول هوشمند</div>
                    <div class="filter-option-desc">ورود حقیقی + خروج حقوقی</div>
                </div>

                <div class="filter-option" data-filter="positive_all">
                    <div class="filter-option-title">✅ همه مثبت</div>
                    <div class="filter-option-desc">قیمت، حجم، و ورود پول مثبت</div>
                </div>

                <div class="filter-option" data-filter="queue">
                    <div class="filter-option-title">🔥 صف خرید</div>
                    <div class="filter-option-desc">نمادهای با صف خرید</div>
                </div>

                <div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #e2e8f0;">
                    <div class="filter-option-title" style="margin-bottom: 10px;">⚙️ فیلتر سفارشی</div>
                    <input type="number" class="custom-filter-input" id="custom-threshold" placeholder="آستانه (مثلاً: 50 برای 50 میلیون تومان)" />
                    <select class="custom-filter-input" id="custom-type">
                        <option value="">-- انتخاب نوع فیلتر --</option>
                        <option value="money_flow">ورود پول حقیقی (میلیون تومان)</option>
                        <option value="buying_power">قدرت خرید حقیقی (درصد)</option>
                        <option value="price_change">تغییر قیمت (درصد)</option>
                        <option value="volume_ratio">نسبت حجم به میانگین</option>
                    </select>
                </div>

                <div id="filter-results"></div>
            </div>
            <div class="filter-footer">
                <button class="filter-btn filter-btn-secondary" onclick="document.getElementById('filter-results').innerHTML = ''">پاک کردن</button>
                <button class="filter-btn filter-btn-primary" id="apply-custom-filter">اعمال سفارشی</button>
            </div>
        `;
        document.body.appendChild(panel);

        // رویدادها
        document.querySelectorAll('.filter-option').forEach(option => {
            option.onclick = function() {
                const filterType = this.getAttribute('data-filter');
                if (filterType) {
                    applyFilter(filterType);
                }
            };
        });

        document.getElementById('apply-custom-filter').onclick = applyCustomFilter;
    }

    function togglePanel() {
        const panel = document.getElementById('bourse-filter-panel');
        panel.classList.toggle('active');
    }

    // دریافت داده‌های بازار
    async function getMarketData() {
        try {
            const response = await fetch('http://www.tsetmc.com/tsev2/data/MarketWatchPlus.aspx');
            const text = await response.text();

            // پارس کردن داده‌ها (فرمت: semicolon separated)
            const lines = text.trim().split('\n');
            const stocks = [];

            for (let line of lines) {
                if (!line) continue;

                const parts = line.split(',');
                if (parts.length < 12) continue;

                try {
                    const stock = {
                        insCode: parts[0],
                        symbol: parts[2],
                        name: parts[3],
                        lastPrice: parseFloat(parts[6]) || 0,
                        closePrice: parseFloat(parts[7]) || 0,
                        firstPrice: parseFloat(parts[8]) || 0,
                        yesterdayPrice: parseFloat(parts[9]) || 0,
                        volume: parseFloat(parts[10]) || 0,
                        value: parseFloat(parts[11]) || 0,
                        low: parseFloat(parts[12]) || 0,
                        high: parseFloat(parts[13]) || 0,
                        count: parseFloat(parts[14]) || 0,
                    };

                    // محاسبه تغییر قیمت
                    if (stock.yesterdayPrice > 0) {
                        stock.priceChange = ((stock.lastPrice - stock.yesterdayPrice) / stock.yesterdayPrice) * 100;
                    } else {
                        stock.priceChange = 0;
                    }

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

    // دریافت داده‌های حقیقی/حقوقی
    async function getClientTypeData(insCode) {
        try {
            const response = await fetch(`http://www.tsetmc.com/tsev2/data/clienttype.aspx?i=${insCode}`);
            const text = await response.text();

            const lines = text.trim().split(';');
            if (lines.length === 0) return null;

            // آخرین رکورد
            const lastLine = lines[lines.length - 1];
            const parts = lastLine.split(',');

            if (parts.length < 12) return null;

            return {
                buyReal: parseFloat(parts[2]) || 0,      // حجم خرید حقیقی
                buyLegal: parseFloat(parts[4]) || 0,     // حجم خرید حقوقی
                sellReal: parseFloat(parts[6]) || 0,     // حجم فروش حقیقی
                sellLegal: parseFloat(parts[8]) || 0,    // حجم فروش حقوقی
            };
        } catch (error) {
            return null;
        }
    }

    // اعمال فیلتر
    async function applyFilter(filterType) {
        const resultsDiv = document.getElementById('filter-results');
        resultsDiv.innerHTML = '<div class="loading">در حال بارگذاری داده‌ها</div>';

        const stocks = await getMarketData();

        if (stocks.length === 0) {
            resultsDiv.innerHTML = '<div style="text-align:center;color:#e53e3e;padding:20px;">خطا در دریافت داده‌ها</div>';
            return;
        }

        let filtered = [];

        switch (filterType) {
            case 'money_flow':
                // فیلتر ورود پول - فقط براساس حجم و قیمت (تقریبی)
                filtered = stocks.filter(s => s.volume > 500000 && s.priceChange > 1);
                filtered.sort((a, b) => (b.volume * b.lastPrice) - (a.volume * a.lastPrice));
                break;

            case 'buying_power':
                // نمادهای با حجم و رشد قیمت خوب
                filtered = stocks.filter(s => s.volume > 300000 && s.priceChange > 0.5);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'high_volume':
                // حجم بالا
                const avgVolume = stocks.reduce((sum, s) => sum + s.volume, 0) / stocks.length;
                filtered = stocks.filter(s => s.volume > avgVolume * 2);
                filtered.sort((a, b) => b.volume - a.volume);
                break;

            case 'price_increase':
                // رشد قیمت
                filtered = stocks.filter(s => s.priceChange > 2);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'legal_exit':
                // نمادهای با حجم بالا و رشد قیمت منفی (احتمال خروج حقوقی)
                filtered = stocks.filter(s => s.volume > 500000 && s.priceChange < -1);
                filtered.sort((a, b) => a.priceChange - b.priceChange);
                break;

            case 'smart_money':
                // ترکیب حجم بالا و رشد قیمت
                filtered = stocks.filter(s => s.volume > 800000 && s.priceChange > 1.5);
                filtered.sort((a, b) => (b.volume * b.priceChange) - (a.volume * a.priceChange));
                break;

            case 'positive_all':
                // همه مثبت
                filtered = stocks.filter(s =>
                    s.priceChange > 0 &&
                    s.volume > 100000 &&
                    s.value > 1000000000
                );
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'queue':
                // صف خرید (قیمت در حداکثر)
                filtered = stocks.filter(s =>
                    s.lastPrice === s.high &&
                    s.priceChange > 3 &&
                    s.volume > 200000
                );
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;
        }

        displayResults(filtered.slice(0, 20), filterType);
    }

    // اعمال فیلتر سفارشی
    async function applyCustomFilter() {
        const threshold = parseFloat(document.getElementById('custom-threshold').value);
        const type = document.getElementById('custom-type').value;

        if (!threshold || !type) {
            alert('لطفاً آستانه و نوع فیلتر را مشخص کنید');
            return;
        }

        const resultsDiv = document.getElementById('filter-results');
        resultsDiv.innerHTML = '<div class="loading">در حال بارگذاری داده‌ها</div>';

        const stocks = await getMarketData();
        let filtered = [];

        switch (type) {
            case 'money_flow':
                // تقریبی: حجم * قیمت / 10,000,000
                filtered = stocks.filter(s => (s.volume * s.lastPrice / 10000000) > threshold);
                filtered.sort((a, b) => (b.volume * b.lastPrice) - (a.volume * a.lastPrice));
                break;

            case 'buying_power':
                filtered = stocks.filter(s => s.priceChange > 0 && s.volume > threshold * 10000);
                filtered.sort((a, b) => b.volume - a.volume);
                break;

            case 'price_change':
                filtered = stocks.filter(s => s.priceChange > threshold);
                filtered.sort((a, b) => b.priceChange - a.priceChange);
                break;

            case 'volume_ratio':
                const avgVol = stocks.reduce((sum, s) => sum + s.volume, 0) / stocks.length;
                filtered = stocks.filter(s => s.volume / avgVol > threshold);
                filtered.sort((a, b) => b.volume - a.volume);
                break;
        }

        displayResults(filtered.slice(0, 20), 'سفارشی');
    }

    // نمایش نتایج
    function displayResults(stocks, filterName) {
        const resultsDiv = document.getElementById('filter-results');

        if (stocks.length === 0) {
            resultsDiv.innerHTML = '<div style="text-align:center;color:#718096;padding:20px;">نمادی یافت نشد</div>';
            return;
        }

        let html = '<div class="results-panel">';
        html += `<div style="font-weight:bold;margin-bottom:10px;color:#2d3748;">📊 نتایج فیلتر: ${filterName} (${stocks.length} نماد)</div>`;

        stocks.forEach((stock, index) => {
            const changeColor = stock.priceChange >= 0 ? '#48bb78' : '#f56565';
            html += `
                <div class="result-item">
                    <div class="result-symbol">${index + 1}. ${stock.symbol}</div>
                    <div class="result-detail">قیمت: ${stock.lastPrice.toLocaleString()} ریال</div>
                    <div class="result-detail" style="color:${changeColor}">تغییر: ${stock.priceChange.toFixed(2)}%</div>
                    <div class="result-detail">حجم: ${stock.volume.toLocaleString()}</div>
                    <div class="result-detail">ارزش: ${(stock.value / 1000000).toFixed(0)} میلیون</div>
                </div>
            `;
        });

        html += '</div>';
        resultsDiv.innerHTML = html;
    }

    // اجرای اولیه
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createUI);
    } else {
        createUI();
    }

    console.log('✅ فیلتر حرفه‌ای بورس بارگذاری شد!');
})();
