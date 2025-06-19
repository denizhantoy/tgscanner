import asyncio
from datetime import datetime
import requests
import pandas as pd
import os
from tradingview_ta import TA_Handler, Interval

class MultiIntervalUpdater:
    def __init__(self, intervals):
        """
        intervals: Çalışma aralıklarının listesi (saniye cinsinden).
        """
        self.intervals = intervals  # Çalışma aralıkları
        self.current_directory = os.getcwd()  # Dosya konumunu alır

    async def fetch_data(self, interval, interval_name):
        """
        Verileri çeker ve işleme alır.
        interval: Çalışma aralığı
        interval_name: TradingView interval adı (ör: INTERVAL_15_MINUTES)
        """
        while True:
            now = datetime.now()
            zaman = now.strftime("%d-%m-%y %H:%M:%S")
            print(f"{interval_name} Güncelleme başladı: {zaman}")
            url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            try:
                r = requests.get(url)
                result = r.json()
            except Exception as e:
                print(f"{interval_name} Veri çekilirken hata oluştu: {e}")
                await asyncio.sleep(interval)
                continue
            symbols = []
            df = pd.DataFrame(result)
            for i in df['symbol']:
                symbols.append(i)
            data = []
            for i in symbols:
                handler = TA_Handler(symbol=i, screener="crypto", exchange="BINANCE", interval=interval_name)
                try:
                    ta = handler.get_indicators()
                    data.append({"symbol":i,"recommendother":ta['Recommend.Other'],"recommendall":ta['Recommend.All'],"recommendma":ta['Recommend.MA'],"rsi":ta['RSI'],"rsi[1]":ta['RSI[1]'],"stochk":ta['Stoch.K'],"stochd":ta['Stoch.D'],"stochk[1]":ta['Stoch.K[1]'],"stochd[1]":ta['Stoch.D[1]'],"cci20":ta['CCI20'],"cci20[1]":ta['CCI20[1]'],"adx":ta['ADX'],"adx+di":ta['ADX+DI'],"adx-di":ta['ADX-DI'],"adx+di[1]":ta['ADX+DI[1]'],"adx-di[1]":ta['ADX-DI[1]'],"ao":ta['AO'],"ao[1]":ta['AO[1]'],"mom":ta['Mom'],"mom[1]":ta['Mom[1]'],"macd":ta['MACD.macd'],"signal":ta['MACD.signal'],"recstochrsi":ta['Rec.Stoch.RSI'],"stochrsik":ta['Stoch.RSI.K'],"recwr":ta['Rec.WR'],"wr":ta['W.R'],"recbbpower":ta['Rec.BBPower'],"bbpower":ta['BBPower'],"recuo":ta['Rec.UO'],"uo":ta['UO'],"close":ta['close'],"ema5":ta['EMA5'],"sma5":ta['SMA5'],"ema10":ta['EMA10'],"sma10":ta['SMA10'],"ema20":ta['EMA20'],"sma20":ta['SMA20'],"ema30":ta['EMA30'],"sma30":ta['SMA30'],"ema50":ta['EMA50'],"sma50":ta['SMA50'],"ema100":ta['EMA100'],"sma100":ta['SMA100'],"ema200":ta['EMA200'],"sma200":ta['SMA200'],"recichimoku":ta['Rec.Ichimoku'],"ichimokubline":ta['Ichimoku.BLine'],"rec.vwma":ta['Rec.VWMA'],"vwma":ta['VWMA'],"rechullma9":ta['Rec.HullMA9'],"hullma9":ta['HullMA9'],"pivotmclassics3":ta['Pivot.M.Classic.S3'],"pivotmclassics2":ta['Pivot.M.Classic.S2'],"pivotmclassics1":ta['Pivot.M.Classic.S1'],"pivotmclassicmiddle":ta['Pivot.M.Classic.Middle'],"pivotmclassicr1":ta['Pivot.M.Classic.R1'],"pivotmclassicr2":ta['Pivot.M.Classic.R2'],"pivotmclassicr3":ta['Pivot.M.Classic.R3'],"pivotmfibonaccis3":ta['Pivot.M.Fibonacci.S3'],"pivotmfibonaccis2":ta['Pivot.M.Fibonacci.S2'],"pivotmfibonaccis1":ta['Pivot.M.Fibonacci.S1'],"pivotmfibonaccimiddle":ta['Pivot.M.Fibonacci.Middle'],"pivotmfibonaccir1":ta['Pivot.M.Fibonacci.R1'],"pivotmfibonaccir2":ta['Pivot.M.Fibonacci.R2'],"pivotmfibonaccir3":ta['Pivot.M.Fibonacci.R3'],"pivotmcamarillas3":ta['Pivot.M.Camarilla.S3'],"pivotmcamarillas2":ta['Pivot.M.Camarilla.S2'],"pivotmcamarillas1":ta['Pivot.M.Camarilla.S1'],"pivotmcamarillamiddle":ta['Pivot.M.Camarilla.Middle'],"pivotmcamarillar1":ta['Pivot.M.Camarilla.R1'],"pivotmcamarillar2":ta['Pivot.M.Camarilla.R2'],"pivotmcamarillar3":ta['Pivot.M.Camarilla.R3'],"pivotmwoodies3":ta['Pivot.M.Woodie.S3'],"pivotmwoodies2":ta['Pivot.M.Woodie.S2'],"pivotmwoodies1":ta['Pivot.M.Woodie.S1'],"pivotmwoodiemiddle":ta['Pivot.M.Woodie.Middle'],"pivotmwoodier1":ta['Pivot.M.Woodie.R1'],"pivotmwoodier2":ta['Pivot.M.Woodie.R2'],"pivotmwoodier3":ta['Pivot.M.Woodie.R3'],"pivotmdemarks1":ta['Pivot.M.Demark.S1'],"pivotmdemarkmiddle":ta['Pivot.M.Demark.Middle'],"pivotmdemarkr1":ta['Pivot.M.Demark.R1'],"open":ta['open'],"psar":ta['P.SAR'],   "bblower":ta['BB.lower'],"bbupper":ta['BB.upper'],"ao[2]":ta['AO[2]'],"volume":ta['volume'],"change":ta['change'],"low":ta['low'],"high":ta['high']})
                    print(data)
                except Exception as e:
                    continue
            df = pd.DataFrame.from_dict(data)
            file_path = os.path.join(self.current_directory, f"indicators_{interval_name}.xlsx")
            df.to_excel(file_path, index=False)
            print(f"{interval_name} Güncelleme tamamlandı: {zaman}")
            await asyncio.sleep(interval)

    async def run(self):
        """
        Belirtilen tüm aralıklar için güncelleme görevlerini başlatır.
        """
        tasks = []
        for interval_name, interval_seconds in self.intervals.items():
            tasks.append(asyncio.create_task(self.fetch_data(interval_seconds, interval_name)))
        await asyncio.gather(*tasks)

# Örnek kullanım
if __name__ == "__main__":
    # Aralıklar ve süreler (saniye cinsinden)
    intervals = {
        Interval.INTERVAL_5_MINUTES: 5 * 60,
        Interval.INTERVAL_15_MINUTES: 15 * 60,
        Interval.INTERVAL_1_HOUR: 60 * 60,
        Interval.INTERVAL_4_HOURS: 4 * 60 * 60,
        Interval.INTERVAL_1_DAY: 24 * 60 * 60,
    }

    updater = MultiIntervalUpdater(intervals)

    try:
        asyncio.run(updater.run())
    except KeyboardInterrupt:
        print("Program durduruldu.")
