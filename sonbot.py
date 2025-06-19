import os
import asyncio
import pandas as pd
import requests
from datetime import datetime
from tradingview_ta import TA_Handler, Interval
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.exceptions import MessageNotModified

# --- Configuration --- #
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '5648816353:AAG34-IieyCzu0NIPR-LCpgJ2oZ-uC81JyU')
ITEMS_PER_PAGE = 10
TIMEFRAME_MAP = {
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY
}
DEFAULT_TIMEFRAME = "15m"

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
user_data = {}
current_timeframes = {}  # Store user's selected timeframes

# --- Helper Functions --- #
def get_file_path(timeframe):
    """Get full path to data file for specific timeframe"""
    return os.path.join(os.getcwd(), f"indicators_{timeframe}.xlsx")

def create_timeframe_keyboard():
    """Create keyboard for timeframe selection"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton("5 Dakika", callback_data="tf_5m"),
        InlineKeyboardButton("15 Dakika", callback_data="tf_15m"),
        InlineKeyboardButton("1 Saat", callback_data="tf_1h"),
        InlineKeyboardButton("4 Saat", callback_data="tf_4h"),
        InlineKeyboardButton("1 Gün", callback_data="tf_1d")
    ]
    keyboard.add(*buttons)
    return keyboard

def create_pagination_keyboard(current_page, total_pages):
    """Create navigation buttons for pagination"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Önceki", callback_data=f"page_{current_page-1}"))
    
    buttons.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="current"))
    
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Sonraki ➡️", callback_data=f"page_{current_page+1}"))
    
    keyboard.add(*buttons)
    return keyboard

async def update_data_for_timeframe(timeframe, message):
    """Update data for specific timeframe"""
    interval = TIMEFRAME_MAP[timeframe]
    start_time = datetime.now()
    msg = await message.answer(f"🔄 *{timeframe} verileri güncelleniyor...*", parse_mode="Markdown")
    
    try:
        # Fetch symbol data from Binance
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        response = requests.get(url)
        response.raise_for_status()
        symbols = [item['symbol'] for item in response.json()]
        
        # Collect technical indicators
        indicators = []
        for symbol in symbols[:100]:  # Limit to 100 for performance
            handler = TA_Handler(
                symbol=symbol,
                screener="crypto",
                exchange="BINANCE",
                interval=interval
            )
            
            try:
                ta_data = handler.get_indicators()
                indicators.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "close": ta_data['close'],
                    "rsi": ta_data['RSI'],
                    "adx": ta_data['ADX'],
                    "volume": ta_data['volume'],
                    "ema20": ta_data.get('EMA20', None),
                    "sma50": ta_data.get('SMA50', None),
                    "macd": ta_data.get('MACD.macd', None),
                    "stoch_k": ta_data.get('Stoch.K', None),
                    "stoch_d": ta_data.get('Stoch.D', None)
                })
            except Exception as e:
                continue
        
        # Save to Excel
        df = pd.DataFrame(indicators)
        df.to_excel(get_file_path(timeframe), index=False)
        
        duration = (datetime.now() - start_time).total_seconds()
        await msg.edit_text(
            f"✅ *{timeframe} verileri güncellendi!*\n\n"
            f"• Toplam kayıt: {len(df)}\n"
            f"• Süre: {duration:.2f} saniye",
            parse_mode="Markdown"
        )
        return df
        
    except Exception as e:
        await msg.edit_text(f"❌ *{timeframe} güncelleme hatası:* {str(e)}", parse_mode="Markdown")
        return None

# --- Command Handlers --- #
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Send welcome message with timeframe selection"""
    welcome_text = (
        "📈 **Çoklu Zaman Aralıklı Kripto Analiz Botu**\n\n"
        "Önce analiz yapmak istediğiniz zaman aralığını seçin:\n\n"
        "• 5m - Kısa vadeli işlemler\n"
        "• 15m - Orta vadeli işlemler (Varsayılan)\n"
        "• 1h - Uzun vadeli işlemler\n"
        "• 4h/1d - Stratejik analiz"
    )
    
    keyboard = create_timeframe_keyboard()
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=keyboard)

@dp.message_handler(commands=['guncelle'])
async def update_data(message: types.Message):
    """Update data for selected timeframe"""
    user_id = message.from_user.id
    timeframe = current_timeframes.get(user_id, DEFAULT_TIMEFRAME)
    await update_data_for_timeframe(timeframe, message)

@dp.message_handler(commands=['sorgu'])
async def custom_query(message: types.Message):
    """Handle custom data queries"""
    user_id = message.from_user.id
    timeframe = current_timeframes.get(user_id, DEFAULT_TIMEFRAME)
    query = message.get_args()
    
    if not query:
        await message.reply(
            f"❌ Lütfen bir sorgu koşulu girin.\nÖrnek: `/sorgu rsi < 30`\n\n"
            f"Şu anki zaman aralığı: **{timeframe}**",
            parse_mode="Markdown"
        )
        return
    
    try:
        # Load and process data
        file_path = get_file_path(timeframe)
        if not os.path.exists(file_path):
            await message.reply(f"❌ {timeframe} verileri bulunamadı. Önce /guncelle komutuyla verileri güncelleyin.")
            return
            
        df = pd.read_excel(file_path)
        result = df.query(query.lower())
        
        if result.empty:
            await message.reply(f"🔍 {timeframe} zaman aralığında koşullara uygun veri bulunamadı.")
            return
        
        # Prepare pagination
        pages = [result[i:i+ITEMS_PER_PAGE] for i in range(0, len(result), ITEMS_PER_PAGE)]
        user_data[user_id] = {
            "pages": pages,
            "current_page": 0,
            "query": query,
            "timeframe": timeframe,
            "message_id": message.message_id
        }
        
        # Show first page
        await show_query_page(user_id, message.chat.id)
        
    except Exception as e:
        await message.reply(
            f"❌ Sorgu hatası: {str(e)}\n\n"
            f"Örnek kullanım: `/sorgu rsi > 70`\n"
            f"Zaman aralığı: **{timeframe}**",
            parse_mode="Markdown"
        )

async def show_query_page(user_id, chat_id):
    """Show paginated query results"""
    if user_id not in user_data:
        await bot.send_message(chat_id, "❌ Oturum sona erdi. Lütfen yeni sorgu yapın.")
        return
        
    data = user_data[user_id]
    page = data["pages"][data["current_page"]]
    total_pages = len(data["pages"])
    
    # Format table
    table = page[["symbol", "close", "rsi", "adx"]].to_markdown(index=False)
    text = (
        f"🔍 **Sorgu Sonuçları**\n"
        f"• Zaman Aralığı: **{data['timeframe']}**\n"
        f"• Koşul: `{data['query']}`\n"
        f"• Sayfa: {data['current_page']+1}/{total_pages}\n\n"
        f"```\n{table}\n```"
    )
    
    # Create keyboard
    keyboard = create_pagination_keyboard(data["current_page"], total_pages)
    
    # Edit or send message
    if "response_id" in data:
        try:
            await bot.edit_message_text(
                text, 
                chat_id, 
                data["response_id"], 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except MessageNotModified:
            pass
    else:
        msg = await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)
        user_data[user_id]["response_id"] = msg.message_id

@dp.callback_query_handler(lambda c: c.data.startswith("page_"))
async def pagination_callback(callback: CallbackQuery):
    """Handle pagination navigation"""
    user_id = callback.from_user.id
    if user_id not in user_data:
        await callback.answer("Oturum sona erdi. Lütfen yeni sorgu yapın.")
        return
    
    # Update current page
    new_page = int(callback.data.split("_")[1])
    user_data[user_id]["current_page"] = new_page
    
    # Update display
    await show_query_page(user_id, callback.message.chat.id)
    await callback.answer()

@dp.message_handler(commands=['rsi'])
async def rsi_command(message: types.Message):
    """Show RSI signals"""
    user_id = message.from_user.id
    timeframe = current_timeframes.get(user_id, DEFAULT_TIMEFRAME)
    
    try:
        # Load data
        file_path = get_file_path(timeframe)
        if not os.path.exists(file_path):
            await message.reply(f"❌ {timeframe} verileri bulunamadı. Önce /guncelle komutuyla verileri güncelleyin.")
            return
            
        df = pd.read_excel(file_path)
        
        # Get RSI signals
        oversold = df[df['rsi'] <= 30][['symbol', 'rsi', 'close']]
        overbought = df[df['rsi'] >= 70][['symbol', 'rsi', 'close']]
        
        # Format response
        response_text = f"📊 **{timeframe} RSI Sinyalleri**\n\n"
        
        if not oversold.empty:
            response_text += "⬇️ *Aşırı Satım (RSI ≤ 30)*\n"
            response_text += oversold.to_markdown(index=False) + "\n\n"
        else:
            response_text += "⚠️ Aşırı satım sinyali bulunamadı\n\n"
        
        if not overbought.empty:
            response_text += "⬆️ *Aşırı Alım (RSI ≥ 70)*\n"
            response_text += overbought.to_markdown(index=False)
        else:
            response_text += "⚠️ Aşırı alım sinyali bulunamadı"
        
        await message.reply(f"```{response_text}```", parse_mode="Markdown")
        
    except Exception as e:
        await message.reply(f"❌ RSI sorgu hatası: {str(e)}")

@dp.message_handler(commands=['adx'])
async def adx_command(message: types.Message):
    """Show ADX signals"""
    user_id = message.from_user.id
    timeframe = current_timeframes.get(user_id, DEFAULT_TIMEFRAME)
    
    try:
        # Load data
        file_path = get_file_path(timeframe)
        if not os.path.exists(file_path):
            await message.reply(f"❌ {timeframe} verileri bulunamadı. Önce /guncelle komutuyla verileri güncelleyin.")
            return
            
        df = pd.read_excel(file_path)
        strong_trend = df[df['adx'] > 45][['symbol', 'adx', 'close']]
        
        # Format response
        if not strong_trend.empty:
            table = strong_trend.to_markdown(index=False)
            text = (
                f"📈 **{timeframe} Güçlü Trend Sinyalleri (ADX > 45)**\n\n"
                f"```\n{table}\n```"
            )
            await message.reply(text, parse_mode="Markdown")
        else:
            await message.reply(f"⚠️ {timeframe} zaman aralığında ADX > 45 koşulunu sağlayan veri bulunamadı.")
            
    except Exception as e:
        await message.reply(f"❌ ADX sorgu hatası: {str(e)}")

@dp.message_handler(commands=['zaman'])
async def show_timeframe_menu(message: types.Message):
    """Show timeframe selection menu"""
    user_id = message.from_user.id
    current_tf = current_timeframes.get(user_id, DEFAULT_TIMEFRAME)
    
    text = (
        f"⏱️ **Mevcut Zaman Aralığı: {current_tf}**\n\n"
        "Analiz için kullanılacak zaman aralığını seçin:"
    )
    
    keyboard = create_timeframe_keyboard()
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

# --- Callback Handlers --- #
@dp.callback_query_handler(lambda c: c.data.startswith("tf_"))
async def handle_timeframe_selection(callback: CallbackQuery):
    """Handle timeframe selection"""
    user_id = callback.from_user.id
    timeframe = callback.data.split("_")[1]
    
    if timeframe not in TIMEFRAME_MAP:
        await callback.answer("Geçersiz zaman aralığı seçildi")
        return
    
    # Save user's timeframe preference
    current_timeframes[user_id] = timeframe
    await callback.answer(f"Zaman aralığı {timeframe} olarak ayarlandı")
    
    # Edit message to show selection
    await bot.edit_message_text(
        f"✅ **Zaman Aralığı Ayarlandı**\n\n"
        f"Artık tüm analizleriniz **{timeframe}** zaman aralığında yapılacaktır.\n\n"
        "Komutları kullanmaya başlayabilirsiniz:\n"
        "• /rsi - RSI sinyalleri\n"
        "• /adx - ADX trend sinyalleri\n"
        "• /sorgu - Özel sorgu\n"
        "• /guncelle - Verileri yenile",
        callback.message.chat.id,
        callback.message.message_id,
        parse_mode="Markdown"
    )

# --- Scanner Module --- #
class MultiTimeframeScanner:
    def __init__(self):
        self.intervals = {
            "5m": 300,    # 5 minutes in seconds
            "15m": 900,   # 15 minutes
            "1h": 3600,   # 1 hour
            "4h": 14400,  # 4 hours
            "1d": 86400   # 1 day
        }
        self.is_running = False
        
    async def run(self):
        """Run the scanner for all timeframes"""
        self.is_running = True
        while self.is_running:
            try:
                for timeframe, interval in self.intervals.items():
                    start_time = datetime.now()
                    print(f"{timeframe} veri güncellemesi başladı: {start_time}")
                    
                    # Create dummy message for update function
                    class DummyMessage:
                        def __init__(self, chat_id):
                            self.chat_id = chat_id
                            
                        async def answer(self, text, parse_mode=None):
                            print(text)
                            
                    dummy_msg = DummyMessage(0)
                    await update_data_for_timeframe(timeframe, dummy_msg)
                    
                    # Wait for the next interval
                    await asyncio.sleep(interval)
                    
            except Exception as e:
                print(f"Scanner hatası: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying

    def stop(self):
        """Stop the scanner"""
        self.is_running = False

# --- Main Execution --- #
if __name__ == '__main__':
    # Start the scanner in the background
    scanner = MultiTimeframeScanner()
    loop = asyncio.get_event_loop()
    scanner_task = loop.create_task(scanner.run())
    
    try:
        # Start the bot
        executor.start_polling(dp, skip_updates=True)
    except KeyboardInterrupt:
        # Stop scanner when bot is stopped
        scanner.stop()
        scanner_task.cancel()