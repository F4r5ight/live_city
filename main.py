import requests
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import os
import random
from pathlib import Path
import pgeocode
from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz

app = FastAPI()

# Подключаем папку со статическими файлами (звуками)
app.mount("/static", StaticFiles(directory="static"), name="static")

# API-ключи
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEB_CAM_API_KEY = os.getenv("WEB_CAM_API_KEY")

# API-адреса
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
RADIO_URL = "https://de1.api.radio-browser.info/json/stations/byname/"
WEB_CAM_URL = "https://api.windy.com/api/webcams/v3/webcams"

# Папка со звуками
SOUNDS_DIR = Path("static/sounds")


def get_timezone_by_city(city: str, country: str = "RU"):
    """
    Получает временную зону города через координаты.
    """
    nomi = pgeocode.Nominatim(country)
    location = nomi.query_location(city)

    if location is None or location.latitude is None or location.longitude is None:
        return None

    lat, lon = location.latitude, location.longitude
    tf = TimezoneFinder()
    timezone = tf.timezone_at(lng=lon, lat=lat)

    return timezone


def get_local_time(city: str, country: str = "RU"):
    """
    Определяет текущее время в городе по его временной зоне.
    """
    timezone = get_timezone_by_city(city, country)

    if not timezone:
        return None

    tz = pytz.timezone(timezone)
    local_time = datetime.now(tz)

    return local_time.hour


@app.get("/weather")
def get_weather(city: str):
    """
    Получает текущую погоду в указанном городе.
    """
    weather_response = requests.get(
        WEATHER_URL,
        params={"q": city, "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru"},
    )
    if weather_response.status_code != 200:
        return {"error": "Город не найден"}

    weather_data = weather_response.json()

    return {
        "city": city,
        "temperature": weather_data["main"]["temp"],
        "feels_like": weather_data["main"]["feels_like"],
        "weather": weather_data["weather"][0]["description"],
        "humidity": weather_data["main"]["humidity"],
        "wind_speed": weather_data["wind"]["speed"],
        "pressure": round(weather_data["main"]["pressure"] * 0.75006, 2),
    }


@app.get("/radio")
def get_radio(city: str):
    """
    Получает ссылку на радио по названию города.
    """
    radio_response = requests.get(RADIO_URL + city)
    radio_data = radio_response.json()

    if not radio_data:
        return {"error": "Радиостанции не найдены"}

    return {"city": city, "radio_url": radio_data[0]["url"]}


@app.get("/camera")
def get_camera(city: str):
    """
    Получает доступные веб-камеры для указанного города.
    """
    headers = {"X-WINDY-API-KEY": WEB_CAM_API_KEY}
    params = {"q": city, "show": "webcams:location,player"}
    response = requests.get(WEB_CAM_URL, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Ошибка запроса к API")

    data = response.json()

    if "result" not in data or "webcams" not in data["result"]:
        return {"error": "Камеры не найдены"}

    webcams = data["result"]["webcams"]
    if not webcams:
        return {"error": "Камеры не найдены"}

    return {
        "city": city,
        "webcams": [
            {
                "id": cam["id"],
                "title": cam["title"],
                "location": cam["location"],
                "player": cam["player"],
            }
            for cam in webcams
        ],
    }


@app.get("/city-sound")
def get_city_sound(city: str):
    """
    Выбирает и отдаёт случайный звук города в зависимости от времени суток.
    """
    hour = get_local_time(city)

    if hour is None:
        return {"error": "Не удалось определить время для указанного города"}

    # Определяем день или ночь
    if 6 <= hour < 20:
        sound_files = list(SOUNDS_DIR.glob("city_day*.mp3"))
    else:
        sound_files = list(SOUNDS_DIR.glob("city_night*.mp3"))

    if not sound_files:
        raise HTTPException(status_code=404, detail="Нет доступных звуков")

    sound_file = random.choice(sound_files)
    sound_url = f"/static/sounds/{sound_file.name}"

    return {"city": city, "time": hour, "sound_url": sound_url}
