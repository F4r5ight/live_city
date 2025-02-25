from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import random
from pathlib import Path
import pgeocode
from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz
import requests
import json

app = FastAPI()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настраиваем Jinja2 для шаблонов HTML
templates = Jinja2Templates(directory="templates")

# Ключи API из переменных окружения
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "YOUR_DEFAULT_API_KEY")
WEB_CAM_API_KEY = os.getenv("WEB_CAM_API_KEY", "YOUR_DEFAULT_API_KEY")

# URLs для внешних API
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
RADIO_URL = "https://de1.api.radio-browser.info/json/stations/byname/"
WINDY_API_URL = "https://api.windy.com/api/webcams/v3/webcams"

# Директория звуков
SOUNDS_DIR = Path("static")


@app.get("/get_timezone_by_city")
def get_timezone_by_city(city: str, country: str = "RU"):
    try:
        # Заменяем дефис на пробел для корректного поиска
        city_formatted = city.replace("-", " ")

        # Инициализируем pgeocode для поиска городов в указанной стране
        nomi = pgeocode.Nominatim(country)
        location = nomi.query_location(city_formatted)

        # Проверяем, найдены ли координаты
        if (
                location.empty
                or location.latitude.isna().all()
                or location.longitude.isna().all()
        ):
            # Если не нашли в указанной стране, пробуем США и другие страны
            if country == "RU":
                return get_timezone_by_city(city, "US")
            elif country == "US":
                return get_timezone_by_city(city, "GB")  # Пробуем Великобританию
            elif country == "GB":
                return get_timezone_by_city(city, "FR")  # Пробуем Францию
            else:
                # Возвращаем фиксированную временную зону для неизвестного города
                return {"timezone": "Europe/Moscow"}  # Дефолтная зона

        # Берём первые найденные координаты
        latitude = location.latitude.iloc[0]
        longitude = location.longitude.iloc[0]

        # Определяем часовой пояс
        tz_finder = TimezoneFinder()
        timezone = tz_finder.timezone_at(lng=longitude, lat=latitude)

        if not timezone:
            return {"timezone": "Europe/Moscow"}  # Дефолтная зона если не определилась

        return {"timezone": timezone}
    except Exception as e:
        print(f"Ошибка при определении часового пояса: {e}")
        return {"timezone": "Europe/Moscow"}  # Дефолтная зона при любой ошибке


@app.get("/get_local_time")
def get_local_time(city: str, country: str = "RU"):
    try:
        timezone_response = get_timezone_by_city(city, country)

        if "timezone" not in timezone_response:
            # Дефолтная московская зона, если не удалось определить
            tz = pytz.timezone("Europe/Moscow")
        else:
            tz = pytz.timezone(timezone_response["timezone"])

        local_time = datetime.now(tz)

        return {
            "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
            "hour": local_time.hour,  # Добавляем "hour" в ответ
        }
    except Exception as e:
        print(f"Ошибка при получении времени: {e}")
        # Дефолтный ответ при любой ошибке
        return {
            "local_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "hour": datetime.now().hour,
        }


@app.get("/weather")
def get_weather(city: str):
    try:
        # Заменяем дефис на пробел для API запроса
        city_formatted = city.replace("-", " ")

        weather_response = requests.get(
            WEATHER_URL,
            params={"q": city_formatted, "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru"},
        )

        if weather_response.status_code != 200:
            # Для демонстрации будем возвращать мок-данные при ошибке
            return {
                "city": city,
                "temperature": 20,
                "feels_like": 18,
                "weather": "ясно",
                "humidity": 65,
                "wind_speed": 3.5,
                "pressure": 760,
            }

        weather_data = weather_response.json()

        try:
            main_data = weather_data.get("main", {})
            if "temp" not in main_data:
                raise KeyError("Температура не найдена")

            temperature = main_data["temp"]
            feels_like = main_data["feels_like"]
            weather = weather_data["weather"][0]["description"]
            humidity = main_data["humidity"]
            wind_speed = weather_data["wind"]["speed"]
            pressure = round(main_data["pressure"] * 0.75006, 2)

            return {
                "city": city,
                "temperature": temperature,
                "feels_like": feels_like,
                "weather": weather,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "pressure": pressure,
            }

        except KeyError as e:
            # Возвращаем мок-данные при ошибке структуры данных
            return {
                "city": city,
                "temperature": 20,
                "feels_like": 18,
                "weather": "ясно",
                "humidity": 65,
                "wind_speed": 3.5,
                "pressure": 760,
            }

    except Exception as e:
        print(f"Ошибка при получении погоды: {e}")
        # Возвращаем мок-данные при любой ошибке
        return {
            "city": city,
            "temperature": 20,
            "feels_like": 18,
            "weather": "ясно",
            "humidity": 65,
            "wind_speed": 3.5,
            "pressure": 760,
        }


@app.get("/radio")
def get_radio(city: str):
    try:
        # Заменяем дефис на пробел для API запроса
        city_formatted = city.replace("-", " ")

        radio_response = requests.get(RADIO_URL + city_formatted)
        radio_data = radio_response.json()

        if not radio_data:
            # Пробуем более общий поиск (например, по стране)
            # Для New-York ищем USA
            if "New-York" in city or "New York" in city:
                radio_response = requests.get(RADIO_URL + "USA")
                radio_data = radio_response.json()
            elif "Moscow" in city:
                radio_response = requests.get(RADIO_URL + "Russia")
                radio_data = radio_response.json()

        if not radio_data:
            # Дефолтная радиостанция
            return {"city": city, "radio_url": "https://online.radiorecord.ru:8102/rr_320"}

        return {"city": city, "radio_url": radio_data[0]["url"]}
    except Exception as e:
        print(f"Ошибка при получении радио: {e}")
        # Дефолтная радиостанция при любой ошибке
        return {"city": city, "radio_url": "https://online.radiorecord.ru:8102/rr_320"}


@app.get("/radio_stations")
def get_radio_stations(city: str):
    """Получает список радиостанций для города"""
    try:
        # Заменяем дефис на пробел для API запроса
        city_formatted = city.replace("-", " ")

        radio_response = requests.get(RADIO_URL + city_formatted)
        radio_data = radio_response.json()

        if not radio_data:
            # Пробуем более общий поиск
            if "New-York" in city or "New York" in city:
                radio_response = requests.get(RADIO_URL + "USA")
                radio_data = radio_response.json()
            elif "Moscow" in city:
                radio_response = requests.get(RADIO_URL + "Russia")
                radio_data = radio_response.json()

        if not radio_data:
            # Возвращаем дефолтные данные
            return {"city": city, "stations": [
                {
                    "name": "Radio Record",
                    "stream_url": "https://online.radiorecord.ru:8102/rr_320",
                    "tags": "dance,electronic",
                    "country": "Russia",
                    "language": "ru",
                    "votes": 100,
                    "frequency": "320 kbps",
                }
            ]}

        # Формируем список станций с нужной информацией
        stations = [
            {
                "name": station.get("name", "Неизвестная станция"),
                "stream_url": station.get("url", ""),
                "tags": station.get("tags", ""),
                "country": station.get("country", ""),
                "language": station.get("language", ""),
                "votes": station.get("votes", 0),
                "frequency": f"{station.get('bitrate', 0)} kbps",
            }
            for station in radio_data[:10]  # Берем первые 10 станций
        ]

        return {"city": city, "stations": stations}
    except Exception as e:
        print(f"Ошибка при получении списка радиостанций: {e}")
        # Возвращаем дефолтные данные при любой ошибке
        return {"city": city, "stations": [
            {
                "name": "Radio Record",
                "stream_url": "https://online.radiorecord.ru:8102/rr_320",
                "tags": "dance,electronic",
                "country": "Russia",
                "language": "ru",
                "votes": 100,
                "frequency": "320 kbps",
            }
        ]}


@app.get("/city-sound")
async def city_sound(time_of_day: str):
    """Возвращает случайный звуковой файл в зависимости от времени суток"""
    try:
        if time_of_day not in ["day", "night"]:
            time_of_day = "day"  # Дефолт - день

        day_sounds = [
            "city_day1.mp3",
            "city_day2.mp3",
            "city_day3.mp3",
            "city_day4.mp3",
            "city_day5.mp3",
            "city_day6.mp3",
            "city_day7.mp3",
            "city_day8.mp3",
        ]
        night_sounds = ["city_night1.mp3", "city_night2.mp3"]

        # Проверяем, существуют ли файлы
        sound_list = day_sounds if time_of_day == "day" else night_sounds
        available_sounds = []

        for sound in sound_list:
            if (SOUNDS_DIR / sound).exists():
                available_sounds.append(sound)

        if not available_sounds:
            # Если нет реальных звуков, возвращаем виртуальный URL
            return {"sound_url": "virtual_sound.mp3"}

        sound_file = random.choice(available_sounds)

        # Просто возвращаем имя файла без префикса /static/
        return {"sound_url": sound_file}
    except Exception as e:
        print(f"Ошибка при получении звука: {e}")
        # Дефолтный ответ при любой ошибке
        return {"sound_url": "virtual_sound.mp3"}


@app.get("/webcam_url")
def get_public_webcam(city: str):
    """Возвращает URL на реальную веб-камеру города из Windy.com API"""
    try:
        # Заменяем дефис на пробел для корректного поиска
        city_formatted = city.replace("-", " ")

        # Получаем камеру через Windy API
        result = get_windy_webcam(city_formatted, WEB_CAM_API_KEY)

        if result["success"]:
            # Если найдена веб-камера или изображение
            webcam_data = {
                "webcam_url": result["webcam_url"],
                "is_image": result.get("is_image", False),
                "title": result.get("title", city),
                "location": result.get("location", city)
            }
            return webcam_data
        else:
            # В случае ошибки возвращаем URL из нашего списка чистых камер
            print(f"Ошибка получения камеры с Windy: {result.get('error')}")
            return {"webcam_url": get_clean_webcam_url(city)}
    except Exception as e:
        print(f"Ошибка при получении веб-камеры: {e}")
        return {"webcam_url": get_clean_webcam_url(city)}


def get_windy_webcam(city, api_key):
    """Получение веб-камеры через API Windy.com"""

    # Параметры запроса
    params = {
        "q": city,  # Поиск по названию города
        "show": "webcams:image,player,location",  # Запрашиваем изображение, плеер и местоположение
        "limit": 10  # Увеличиваем лимит для большего выбора
    }

    # Заголовки запроса с API ключом
    headers = {
        "X-WINDY-API-KEY": api_key
    }

    try:
        # Выполняем запрос к API
        response = requests.get(WINDY_API_URL, params=params, headers=headers)

        # Проверяем статус ответа
        if response.status_code == 200:
            data = response.json()

            # Проверяем наличие веб-камер в ответе
            if "result" in data and "webcams" in data["result"] and data["result"]["webcams"]:
                webcams = data["result"]["webcams"]

                # Сначала ищем камеры без рекламы
                for webcam in webcams:
                    if "player" in webcam:
                        player_info = webcam["player"]

                        # Проверка на наличие встроенного видео
                        if "day" in player_info and player_info["day"].get("embed"):
                            return {
                                "success": True,
                                "webcam_url": player_info["day"]["embed"],
                                "title": webcam.get("title", city),
                                "location": webcam.get("location", {}).get("city", city)
                            }

                # Если нет камер с прямой трансляцией, но есть изображения
                if "image" in webcams[0] and webcams[0]["image"].get("current", {}).get("preview"):
                    return {
                        "success": True,
                        "webcam_url": webcams[0]["image"]["current"]["preview"],
                        "is_image": True,
                        "title": webcams[0].get("title", city),
                        "location": webcams[0].get("location", {}).get("city", city)
                    }

            # Если камеры не найдены
            return {
                "success": False,
                "error": "Камеры не найдены для данного города"
            }
        else:
            # Если API вернул ошибку
            return {
                "success": False,
                "error": f"Ошибка API: {response.status_code}",
                "details": response.text
            }

    except Exception as e:
        # В случае других ошибок
        return {
            "success": False,
            "error": f"Исключение: {str(e)}"
        }


def get_clean_webcam_url(city):
    """Возвращает URL чистой веб-камеры без рекламы для города"""
    # Список проверенных трансляций без рекламы
    clean_webcams = {
        # Трансляции из городов на Skylinewebcams (без рекламы)
        "New-York": "https://www.skylinewebcams.com/en/webcam/united-states/new-york/new-york/new-york-skyline.html",
        "Moscow": "https://balticlivecam.com/cameras/russia/moscow/moscow-city-panorama/",
        "Paris": "https://www.viewsurf.com/univers/ville/vue/17333-france-ile-de-france-paris-vue-sur-la-tour-eiffel",
        "London": "https://www.earthtv.com/en/webcam/london-united-kingdom",
        "Barcelona": "https://www.skylinewebcams.com/en/webcam/espana/cataluna/barcelona/barcelona-sagrada-familia.html",
        "Milan": "https://www.skylinewebcams.com/en/webcam/italia/lombardia/milano/duomo-milano.html",
        "Rome": "https://www.skylinewebcams.com/en/webcam/italia/lazio/roma/fontana-di-trevi.html",
        "Venice": "https://www.skylinewebcams.com/en/webcam/italia/veneto/venezia/venezia-canal-grande.html",
        "Tokyo": "https://www.youtube.com/embed/JJ63v1AwSg4",  # Очищенная трансляция Токио
        "Amsterdam": "https://iamsterdam.com/en/how-can-we-help-you/plan-your-trip/digital-city-experience/livecam-dam-square",
        "Prague": "https://www.earthtv.com/en/webcam/prague-czech-republic",
        "Seoul": "https://www.earthtv.com/en/webcam/seoul-south-korea",
        "Sydney": "https://www.webcamsydney.com/",
        "Berlin": "https://www.earthtv.com/en/webcam/berlin-germany",
        "Dubai": "https://www.skylinewebcams.com/en/webcam/united-arab-emirates/dubai/dubai/dubai-skyline.html",
        "Madrid": "https://www.skylinewebcams.com/en/webcam/espana/comunidad-de-madrid/madrid/puerta-del-sol.html",
        "Athens": "https://www.skylinewebcams.com/en/webcam/ellada/attiki/athina/acropolis.html",
        "Vienna": "https://www.viewsurf.com/univers/ville/vue/1312-autriche-vienne-vienne-vue-panoramique",
        "Las-Vegas": "https://www.earthtv.com/en/webcam/las-vegas-usa",
    }

    # Если город в списке, возвращаем его камеру
    if city in clean_webcams:
        return clean_webcams[city]

    # Если города нет в списке, возвращаем случайную камеру из списка
    return random.choice(list(clean_webcams.values()))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница с формой ввода города"""
    return templates.TemplateResponse("index.html", {
        "request": request
    })


@app.get("/city", response_class=HTMLResponse)
async def city_page(request: Request, city: str):
    """HTML-страница с интеграцией фона города, погоды и радио"""
    try:
        # Получаем погоду
        weather_data = get_weather(city)

        # Получаем местное время и определяем время суток
        time_data = get_local_time(city)
        time_of_day = "day" if 6 <= time_data.get("hour", 12) < 18 else "night"

        # Получаем данные о радио
        radio_data = get_radio(city)
        radio_url = None
        if "radio_url" in radio_data:
            radio_url = radio_data["radio_url"]

        # Получаем фоновые звуки
        ambient_sounds = []
        for _ in range(3):  # Получаем 3 разных звука
            sound_data = await city_sound(time_of_day)
            if "sound_url" in sound_data:
                ambient_sounds.append(f"/static/{sound_data['sound_url']}")

        # Получаем URL веб-камеры города
        webcam_data = get_public_webcam(city)
        webcam_url = webcam_data.get("webcam_url")
        is_image = webcam_data.get("is_image", False)

        # Передаем данные в шаблон
        return templates.TemplateResponse("index.html", {
            "request": request,
            "city": city,
            "weather": weather_data,
            "time_of_day": time_of_day,
            "webcam_url": webcam_url,
            "is_image": is_image,
            "radio_url": radio_url,
            "ambient_sounds": json.dumps(ambient_sounds) if ambient_sounds else None
        })

    except Exception as e:
        # В случае ошибки возвращаем страницу с ошибкой
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": True,
            "error_message": str(e),
            "city": city
        })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
