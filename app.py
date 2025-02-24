import requests
import streamlit as st
from streamlit.components.v1 import html


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
    try:
        response = requests.get(
            f"http://localhost:8000/city-sound?time_of_day={time_of_day}"
        )
        if response.status_code == 200:
            return response.json()
        print(f"Ошибка API звука: {response.status_code}")
        return None
    except Exception as e:
        print("Ошибка получения звука:", e)
        return None


def play_ambient_sounds(time_of_day):
    """Создает HTML-код для воспроизведения нескольких звуков города в фоновом режиме"""
    # Получаем несколько звуков для создания плейлиста
    sounds = []
    for _ in range(3):  # Получаем 3 разных звука
        sound_data = get_city_sound(time_of_day)
        if sound_data and "sound_url" in sound_data:
            sounds.append(f"http://localhost:8000/static/{sound_data['sound_url']}")

    if not sounds:
        return None

    # Создаем JavaScript для последовательного воспроизведения звуков с низкой громкостью
    js_code = """
    <script>
        // Массив звуков для воспроизведения
        const soundUrls = %s;
        let currentIndex = 0;
        let audioElement = null;

        // Функция для воспроизведения следующего звука
        function playNextSound() {
            if (audioElement) {
                audioElement.pause();
            }

            if (currentIndex >= soundUrls.length) {
                currentIndex = 0;
            }

            const soundUrl = soundUrls[currentIndex];
            audioElement = new Audio(soundUrl);
            audioElement.volume = 0.15;  // Очень низкая громкость

            // По окончании трека переходим к следующему
            audioElement.onended = function() {
                currentIndex++;
                playNextSound();
            };

            audioElement.play()
                .then(() => console.log('Воспроизводится звук:', soundUrl))
                .catch(err => console.error('Ошибка воспроизведения:', err));
        }

        // Начинаем воспроизведение
        playNextSound();
    </script>
    """ % str(sounds)

    return js_code


# Инициализация session_state
if 'current_city' not in st.session_state:
    st.session_state.current_city = ""
if 'sound_initialized' not in st.session_state:
    st.session_state.sound_initialized = False

st.title("Городская платформа")
st.write("Введите город для получения информации:")
city = st.text_input("Введите город")

if city and city != st.session_state.current_city:
    st.session_state.current_city = city
    st.session_state.sound_initialized = False

    time_of_day = get_city_time_of_day(city)

    if time_of_day and not st.session_state.sound_initialized:
        # Создаем HTML для воспроизведения звуков
        ambient_sounds_js = play_ambient_sounds(time_of_day)
        if ambient_sounds_js:
            html(ambient_sounds_js, height=0)
            st.session_state.sound_initialized = True

    weather = get_weather(city)

    if "error" not in weather:
        st.write(f"Погода в {city}:")
        st.write(f"Температура: {weather['temperature']}°C")
        st.write(f"Ощущается как: {weather['feels_like']}°C")
        st.write(f"Погодные условия: {weather['weather']}")
        st.write(f"Влажность: {weather['humidity']}%")
        st.write(f"Скорость ветра: {weather['wind_speed']} м/с")
        st.write(f"Давление: {weather['pressure']} мм рт. ст.")