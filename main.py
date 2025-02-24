import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import random
import pandas as pd
from pathlib import Path
import pgeocode
from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEB_CAM_API_KEY = os.getenv("WEB_CAM_API_KEY")

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
RADIO_URL = "https://de1.api.radio-browser.info/json/stations/byname/"
WEB_CAM_URL = "https://api.windy.com/api/webcams/v3/webcams"

SOUNDS_DIR = Path("static")


@app.get("/get_timezone_by_city")
def get_timezone_by_city(city: str, country: str = "RU"):
    # Инициализируем pgeocode для поиска городов в указанной стране
    nomi = pgeocode.Nominatim(country)
    location = nomi.query_location(city)

    # Проверяем, найдены ли координаты
    if (
        location.empty
        or location.latitude.isna().all()
        or location.longitude.isna().all()
    ):
        raise HTTPException(status_code=404, detail="Город не найден")

    # Берём первые найденные координаты
    latitude = location.latitude.iloc[0]
    longitude = location.longitude.iloc[0]

    # Определяем часовой пояс
    tz_finder = TimezoneFinder()
    timezone = tz_finder.timezone_at(lng=longitude, lat=latitude)

    if not timezone:
        raise HTTPException(status_code=404, detail="Часовой пояс не найден")

    return {"timezone": timezone}


@app.get("/get_local_time")
def get_local_time(city: str, country: str = "RU"):
    timezone_response = get_timezone_by_city(city, country)

    if "timezone" not in timezone_response:
        raise HTTPException(status_code=404, detail="Часовой пояс не найден")

    tz = pytz.timezone(timezone_response["timezone"])
    local_time = datetime.now(tz)

    return {
        "local_time": local_time.strftime("%Y-%m-%d %H:%M:%S"),
        "hour": local_time.hour,  # Добавляем "hour" в ответ
    }


@app.get("/weather")
def get_weather(city: str):

    weather_response = requests.get(
        WEATHER_URL,
        params={"q": city, "appid": WEATHER_API_KEY, "units": "metric", "lang": "ru"},
    )

    if weather_response.status_code != 200:
        raise HTTPException(status_code=404, detail="Город не найден")

    weather_data = weather_response.json()

    try:
        main_data = weather_data.get("main", {})
        if "temp" not in main_data:
            raise HTTPException(
                status_code=500, detail="Температура не найдена в данных ответа API"
            )

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
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении данных о погоде: {e}"
        )


@app.get("/radio")
def get_radio(city: str):
    radio_response = requests.get(RADIO_URL + city)
    radio_data = radio_response.json()

    if not radio_data:
        return {"error": "Радиостанции не найдены"}

    return {"city": city, "radio_url": radio_data[0]["url"]}


@app.get("/camera")
def get_camera(city: str):
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
async def city_sound(time_of_day: str):
    """Возвращает случайный звуковой файл в зависимости от времени суток"""
    if time_of_day not in ["day", "night"]:
        raise HTTPException(status_code=400, detail="Некорректное значение time_of_day")

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

    sound_file = random.choice(day_sounds if time_of_day == "day" else night_sounds)

    return {"sound_url": f"/static/{sound_file}"}
