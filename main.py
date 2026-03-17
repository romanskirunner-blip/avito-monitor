import requests
from bs4 import BeautifulSoup
import time
import random
from telegram import Bot
import asyncio

# ===== НАСТРОЙКИ =====
TELEGRAM_TOKEN = "8207189240:AAGsNbPOejj0mpmEgPfqvZZY_NBa6Wfp3d8"
CHAT_ID = "7226332475"

# Параметры поиска
QUERY = "iPhone 13"  # ЧТО ИЩЕМ - ИЗМЕНИТЕ НА СВОЁ
CITY = "moskva"      # ГОРОД (moskva, sankt-peterburg, novosibirsk и т.д.)
CHECK_INTERVAL = 600 # Интервал проверки в секундах (600 = 10 минут)

# Хранилище
seen_ids = set()

def parse_avito(query, city="moskva"):
    """Парсинг Avito"""
    new_items = []
    
    try:
        print(f"🔍 [{time.strftime('%H:%M:%S')}] Проверка: {query}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        url = f"https://www.avito.ru/{city}?q={query}"
        
        # Случайная задержка
        delay = random.uniform(3, 7)
        time.sleep(delay)
        
        response = requests.get(url, headers=headers, timeout=20)
        print(f"   📊 Статус: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'lxml')
            items = soup.find_all('div', {'data-marker': 'item'})
            
            print(f"   ✅ Найдено элементов: {len(items)}")
            
            for item in items[:15]:
                try:
                    # ID из ссылки
                    link_elem = item.select_one('a[href*="/items/"]') or item.select_one('a[itemprop="url"]')
                    
                    if not link_elem or 'href' not in link_elem.attrs:
                        continue
                    
                    href = link_elem['href']
                    item_id = None
                    
                    if '_' in href:
                        item_id = href.split('_')[-1].split('?')[0]
                    
                    if not item_id or item_id in seen_ids:
                        continue
                    
                    # Название
                    title_elem = item.select_one('[itemprop="name"]') or item.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else 'Н/Д'
                    
                    if title == 'Н/Д':
                        continue
                    
                    # Цена
                    price = 'Н/Д'
                    price_elem = item.select_one('[itemprop="price"]')
                    if price_elem and 'content' in price_elem.attrs:
                        price = f"{price_elem['content']} ₽"
                    else:
                        price_elem = item.select_one('[data-marker="item-price"]')
                        if price_elem:
                            price = price_elem.get_text(strip=True)
                    
                    # Ссылка
                    if href.startswith('http'):
                        link = href
                    elif href.startswith('/'):
                        link = 'https://www.avito.ru' + href
                    else:
                        link = 'https://www.avito.ru/' + href
                    
                    # Местоположение
                    location_elem = item.select_one('[data-marker="item-address"]')
                    location = location_elem.get_text(strip=True) if location_elem else city.capitalize()
                    
                    # Дата
                    date_elem = item.select_one('[data-marker="item-date"]')
                    date = date_elem.get_text(strip=True) if date_elem else 'Н/Д'
                    
                    # Добавляем
                    new_items.append({
                        'id': item_id,
                        'title': title,
                        'price': price,
                        'location': location,
                        'date': date,
                        'link': link
                    })
                    
                    seen_ids.add(item_id)
                    print(f"   ✨ НОВОЕ: {title[:50]}...")
                    
                except Exception as e:
                    print(f"   ⚠️ Ошибка элемента: {e}")
                    continue
        
        elif response.status_code == 403:
            print(f"   ❌ Код 403 - Avito заблокировал запрос")
        else:
            print(f"   ❌ Неожиданный код: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка парсинга: {e}")
    
    return new_items

async def send_telegram(message):
    """Отправка сообщения в Telegram"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

async def main():
    """Главный цикл мониторинга"""
    
    print("="*60)
    print("🤖 AVITO MONITOR - CLOUD EDITION")
    print(f"🔍 Запрос: {QUERY}")
    print(f"📍 Город: {CITY}")
    print(f"⏱  Интервал: {CHECK_INTERVAL} сек ({CHECK_INTERVAL//60} мин)")
    print("="*60)
    
    # Уведомление о запуске
    await send_telegram(
        f"✅ *Мониторинг запущен!*\n\n"
        f"🔍 Запрос: `{QUERY}`\n"
        f"📍 Город: {CITY}\n"
        f"⏱ Проверка каждые {CHECK_INTERVAL//60} минут"
    )
    
    # Первый запуск
    print("\n🚀 Первоначальная загрузка...")
    items = parse_avito(QUERY, CITY)
    
    if items:
        await send_telegram(f"📊 *Начальная загрузка*\n\nНайдено объявлений: {len(items)}")
        
        # Отправляем первые 3
        for item in items[:3]:
            message = f"""📌 *Объявление*

*{item['title']}*

💰 {item['price']}
📍 {item['location']}
📅 {item['date']}

🔗 [Открыть на Avito]({item['link']})"""
            
            await send_telegram(message)
            await asyncio.sleep(1)
    else:
        await send_telegram("⚠️ При первой загрузке объявления не найдены (возможна блокировка)")
    
    print(f"\n✅ Начальная загрузка завершена")
    print(f"🔄 Переход в режим мониторинга...\n")
    
    # Бесконечный цикл мониторинга
    iteration = 1
    while True:
        try:
            print(f"\n{'='*60}")
            print(f"🔄 Итерация #{iteration}")
            print(f"⏰ Следующая проверка через {CHECK_INTERVAL//60} минут")
            print(f"{'='*60}")
            
            await asyncio.sleep(CHECK_INTERVAL)
            
            items = parse_avito(QUERY, CITY)
            
            if items:
                await send_telegram(f"🆕 *Найдено новых объявлений: {len(items)}*\n🔍 {QUERY}")
                
                for item in items:
                    message = f"""✨ *НОВОЕ ОБЪЯВЛЕНИЕ*

*{item['title']}*

💰 {item['price']}
📍 {item['location']}
📅 {item['date']}

🔗 [Открыть на Avito]({item['link']})"""
                    
                    await send_telegram(message)
                    await asyncio.sleep(1)
            else:
                print(f"   ℹ️ Новых объявлений не найдено")
            
            iteration += 1
            
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Остановлено пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
```

---

## 📁 **Файл 2: `requirements.txt`**
```
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.1.0
python-telegram-bot==21.0.1
