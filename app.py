import streamlit as st
import requests
from fastapi import FastAPI

app = FastAPI()

def get_weather(city):
    try:
        response = requests.get(f"http://localhost:8000/weather?city={city}")
        return (
            response.json()
            if response.status_code == 200
            else {"error": "Ошибка API погоды"}
        )
    except Exception as e:
        print("Ошибка получения погоды:", e)
        return {"error": str(e)}


def get_camera(city):
    try:
        response = requests.get(f"http://localhost:8000/camera?city={city}")
        return (
            response.json()
            if response.status_code == 200
            else {"error": "Ошибка API камер"}
        )
    except Exception as e:
        print("Ошибка получения камеры:", e)
        return {"error": str(e)}


def get_radio(city):
    try:
        response = requests.get(f"http://localhost:8000/radio?city={city}")
        return (
            response.json()
            if response.status_code == 200
            else {"error": "Ошибка API радио"}
        )
    except Exception as e:
        print("Ошибка получения радио:", e)
        return {"error": str(e)}


def get_city_time_of_day(city):
    """Определяет, день или ночь в указанном городе"""
    try:
        response = requests.get(f"http://localhost:8000/get_local_time?city={city}")
        if response.status_code == 200:
            data = response.json()
            local_time = data.get("local_time")

            if not local_time:
                print("Ошибка: нет 'local_time' в ответе", data)
                return None

            # Парсим время из строки
            local_hour = int(local_time.split(" ")[1].split(":")[0])
            return "day" if 6 <= local_hour < 18 else "night"

        print("Ошибка API времени:", response.status_code)
        return None
    except Exception as e:
        print("Ошибка получения времени:", e)
        return None


def get_city_sound(time_of_day):
    """Запрашивает звук в зависимости от времени суток"""
    response = requests.get(
        f"http://localhost:8000/city-sound?time_of_day={time_of_day}"
    )

    try:
        data = response.json()
        st.write(data)  # Вывод ответа API

        if "sound_url" not in data:
            print("Ошибка: нет 'sound_url' в ответе", data)
            return None
        return data
    except Exception as e:
        print("Ошибка получения звука:", e)
        return None


st.title("Городская платформа")
st.write("Введите город для получения информации:")
city = st.text_input("Введите город")

if city:
    time_of_day = get_city_time_of_day(city)

    if time_of_day:
        city_sound = get_city_sound(time_of_day)

        if city_sound and "sound_url" in city_sound:
            sound_url = f"/static/{city_sound['sound_url']}"

            st.markdown(
                """
    <button id="playAudioButton">Запустить звук</button>
    <script>
    document.getElementById("playAudioButton").onclick = function() {
        var audio = new Audio('http://localhost:8000/static/sounds/city_day3.mp3');
        audio.loop = true;
        audio.play();
    }
    </script>
    """,
                unsafe_allow_html=True,
            )

        else:
            st.write("⚠ Ошибка загрузки звука")
    else:
        st.write("⚠ Ошибка получения времени суток для города")

    weather = get_weather(city)

    if "error" not in weather:
        st.write(f"Погода в {city}:")
        st.write(f"Температура: {weather['temperature']}°C")
        st.write(f"Ощущается как: {weather['feels_like']}°C")
        st.write(f"Погодные условия: {weather['weather']}")
        st.write(f"Влажность: {weather['humidity']}%")
        st.write(f"Скорость ветра: {weather['wind_speed']} м/с")
        st.write(f"Давление: {weather['pressure']} мм рт. ст.")
