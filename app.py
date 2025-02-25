import requests
import streamlit as st
from streamlit.components.v1 import html
import base64
import random
import os
import json


def get_weather(city):
    try:
        city_formatted = city.replace("-", " ")
        response = requests.get(f"http://localhost:8000/weather?city={city_formatted}")

        if response.status_code == 200:
            return response.json()
        else:
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
        print("Ошибка получения погоды:", e)
        return {
            "city": city,
            "temperature": 20,
            "feels_like": 18,
            "weather": "ясно",
            "humidity": 65,
            "wind_speed": 3.5,
            "pressure": 760,
        }


def get_radio(city):
    try:
        city_formatted = city.replace("-", " ")
        response = requests.get(f"http://localhost:8000/radio?city={city_formatted}")

        if response.status_code == 200:
            return response.json()
        else:
            return {"city": city, "radio_url": "https://online.radiorecord.ru:8102/rr_320"}
    except Exception as e:
        print("Ошибка получения радио:", e)
        return {"city": city, "radio_url": "https://online.radiorecord.ru:8102/rr_320"}


def get_city_time_of_day(city):
    """Определяет, день или ночь в указанном городе"""
    try:
        city_formatted = city.replace("-", " ")
        response = requests.get(f"http://localhost:8000/get_local_time?city={city_formatted}")

        if response.status_code == 200:
            data = response.json()
            hour = data.get("hour")

            if hour is None:
                return "day"

            return "day" if 6 <= hour < 18 else "night"
        else:
            return "day"
    except Exception as e:
        print("Ошибка получения времени:", e)
        return "day"


def get_city_sound(time_of_day):
    try:
        response = requests.get(
            f"http://localhost:8000/city-sound?time_of_day={time_of_day}"
        )
        if response.status_code == 200:
            return response.json()
        return {"sound_url": "virtual_sound.mp3"}
    except Exception as e:
        print("Ошибка получения звука:", e)
        return {"sound_url": "virtual_sound.mp3"}


def get_webcam_data(city):
    try:
        response = requests.get(f"http://localhost:8000/webcam_url?city={city}")
        if response.status_code == 200:
            data = response.json()
            print(f"Получены данные веб-камеры: {data}")
            return data
        print(f"Ошибка получения веб-камеры, статус: {response.status_code}")
        # Резервные веб-камеры YouTube
        backup_webcams = {
            "New-York": "https://www.youtube.com/embed/1-iS7LArMPA?autoplay=1&mute=1",
            "Moscow": "https://www.youtube.com/embed/cGNrBB87YeU?autoplay=1&mute=1",
            "Paris": "https://www.youtube.com/embed/4qyZLflp-sI?autoplay=1&mute=1",
            "London": "https://www.youtube.com/embed/GhbyiyBZEps?autoplay=1&mute=1",
            "Tokyo": "https://www.youtube.com/embed/JJ63v1AwSg4?autoplay=1&mute=1",
            "Berlin": "https://www.youtube.com/embed/JGkuM4_RKIw?autoplay=1&mute=1",
        }
        if city in backup_webcams:
            return {"webcam_url": backup_webcams[city]}
        # Дефолтная веб-камера
        return {"webcam_url": "https://www.youtube.com/embed/1-iS7LArMPA?autoplay=1&mute=1"}
    except Exception as e:
        print(f"Исключение при получении веб-камеры: {e}")
        return {"webcam_url": "https://www.youtube.com/embed/1-iS7LArMPA?autoplay=1&mute=1"}


def set_background(webcam_url):
    """Устанавливает живую веб-камеру в качестве фона"""
    webcam_html = f"""
    <style>
        .webcam-background {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: -1;
            overflow: hidden;
        }}

        .webcam-background iframe {{
            width: 100%;
            height: 100%;
            border: none;
            position: absolute;
            top: 0;
            left: 0;
            pointer-events: none;
        }}
    </style>

    <div class="webcam-background">
        <iframe 
            src="{webcam_url}" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen
            frameborder="0"
        ></iframe>
    </div>
    """
    st.markdown(webcam_html, unsafe_allow_html=True)


def create_autoplay_radio(radio_url, city_id):
    """Создает радиоплеер с уникальным id для каждого города"""
    radio_js = f"""
    <div style="margin-top: 10px; padding: 0;">
        <h3 style="color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.7); margin-bottom: 10px;">Радио</h3>
        <div style="display: flex; align-items: center; gap: 10px;">
            <button id="toggleRadio_{city_id}" style="width: 40px; height: 40px; border: none; border-radius: 50%; background: #dc3545; color: white; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center; font-size: 20px;">
                ⏹
            </button>
            <div id="volume_container_{city_id}" style="position: relative; display: none;">
                <div style="position: absolute; bottom: 45px; left: 0; background: rgba(0,0,0,0.7); padding: 10px; border-radius: 10px; width: 150px;">
                    <label for="volume_{city_id}" style="color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.7); display: block; margin-bottom: 5px;">Громкость:</label>
                    <input type="range" id="volume_{city_id}" min="0" max="100" value="10" style="width: 100%;">
                </div>
                <button id="volume_btn_{city_id}" style="width: 40px; height: 40px; border: none; border-radius: 50%; background: #007bff; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 20px;">
                    🔊
                </button>
            </div>
        </div>
    </div>

    <script>
        // Создаем уникальные ID для элементов управления
        const radioId = "radio_{city_id}";
        let audioPlayer_{city_id} = null;
        let isPlaying_{city_id} = false;
        const radioUrl_{city_id} = "{radio_url}";
        const toggleButton_{city_id} = document.getElementById('toggleRadio_{city_id}');
        const volumeControl_{city_id} = document.getElementById('volume_{city_id}');
        const volumeContainer_{city_id} = document.getElementById('volume_container_{city_id}');
        const volumeButton_{city_id} = document.getElementById('volume_btn_{city_id}');

        // Функция автозапуска радио
        function startRadio_{city_id}() {{
            if (audioPlayer_{city_id}) {{
                audioPlayer_{city_id}.pause();
                audioPlayer_{city_id} = null;
            }}

            audioPlayer_{city_id} = new Audio(radioUrl_{city_id});
            audioPlayer_{city_id}.volume = volumeControl_{city_id}.value / 100;

            audioPlayer_{city_id}.onerror = function() {{
                console.error('Ошибка воспроизведения радио.');
                isPlaying_{city_id} = false;
                toggleButton_{city_id}.innerHTML = '▶';
                toggleButton_{city_id}.style.background = '#007bff';

                // Показываем контейнер регулировки громкости
                volumeContainer_{city_id}.style.display = 'none';
            }};

            audioPlayer_{city_id}.play().then(function() {{
                isPlaying_{city_id} = true;
                toggleButton_{city_id}.innerHTML = '⏹';
                toggleButton_{city_id}.style.background = '#dc3545';

                // Показываем контейнер регулировки громкости
                volumeContainer_{city_id}.style.display = 'block';
            }}).catch(function(error) {{
                console.error('Ошибка воспроизведения:', error);
                isPlaying_{city_id} = false;
                toggleButton_{city_id}.innerHTML = '▶';
                toggleButton_{city_id}.style.background = '#007bff';

                // Скрываем контейнер регулировки громкости
                volumeContainer_{city_id}.style.display = 'none';
            }});
        }}

        toggleButton_{city_id}.addEventListener('click', function() {{
            if (isPlaying_{city_id}) {{
                // Выключить радио
                if (audioPlayer_{city_id}) {{
                    audioPlayer_{city_id}.pause();
                    audioPlayer_{city_id} = null;
                }}
                isPlaying_{city_id} = false;
                toggleButton_{city_id}.innerHTML = '▶';
                toggleButton_{city_id}.style.background = '#007bff';

                // Скрываем контейнер регулировки громкости
                volumeContainer_{city_id}.style.display = 'none';
            }} else {{
                // Включить радио
                startRadio_{city_id}();
            }}
        }});

        volumeControl_{city_id}.addEventListener('input', function() {{
            if (audioPlayer_{city_id}) {{
                audioPlayer_{city_id}.volume = this.value / 100;
            }}
        }});

        // Обработчик кнопки громкости
        let volumeVisible_{city_id} = false;
        volumeButton_{city_id}.addEventListener('click', function() {{
            const volumePanel = volumeButton_{city_id}.previousElementSibling;
            if (volumeVisible_{city_id}) {{
                volumePanel.style.display = 'none';
                volumeVisible_{city_id} = false;
            }} else {{
                volumePanel.style.display = 'block';
                volumeVisible_{city_id} = true;
            }}
        }});

        // Автозапуск радио при загрузке страницы
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(startRadio_{city_id}, 1000); // Задержка 1 секунда для загрузки страницы
        }});

        // Запускаем радио сразу
        startRadio_{city_id}();
    </script>
    """
    return radio_js


def play_ambient_sounds(time_of_day, city_id):
    sounds = []
    for _ in range(3):  # Получаем 3 разных звука
        sound_data = get_city_sound(time_of_day)
        if sound_data and "sound_url" in sound_data:
            sounds.append(f"http://localhost:8000/static/{sound_data['sound_url']}")

    if not sounds:
        return None

    js_code = f"""
    <script>
        // Массив звуков для воспроизведения
        const soundUrls_{city_id} = {json.dumps(sounds)};
        let currentIndex_{city_id} = 0;
        let audioElement_{city_id} = null;

        // Функция для воспроизведения следующего звука
        function playNextSound_{city_id}() {{
            if (audioElement_{city_id}) {{
                audioElement_{city_id}.pause();
            }}

            if (currentIndex_{city_id} >= soundUrls_{city_id}.length) {{
                currentIndex_{city_id} = 0;
            }}

            const soundUrl = soundUrls_{city_id}[currentIndex_{city_id}];
            audioElement_{city_id} = new Audio(soundUrl);
            audioElement_{city_id}.volume = 0.05;  // Очень низкая громкость (5%)

            // По окончании трека переходим к следующему
            audioElement_{city_id}.onended = function() {{
                currentIndex_{city_id}++;
                playNextSound_{city_id}();
            }};

            audioElement_{city_id}.play()
                .then(() => console.log('Воспроизводится звук:', soundUrl))
                .catch(err => {{
                    console.error('Ошибка воспроизведения:', err);
                    currentIndex_{city_id}++;
                    setTimeout(playNextSound_{city_id}, 1000); // Пробуем следующий звук через секунду
                }});
        }}

        // Начинаем воспроизведение
        playNextSound_{city_id}();
    </script>
    """

    return js_code


st.set_page_config(
    page_title="Городская платформа",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background-color: transparent;
    }
    .main {
        background-color: transparent;
    }
    /* Прозрачный фон для карточек */
    .stTextInput > div > div {
        background-color: rgba(255, 255, 255, 0.7);
    }
    /* Стили для текста заголовков */
    h1, h2, h3 {
        color: white !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.8) !important;
    }
    /* Стили для текста параграфов */
    p, div {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.7) !important;
    }
    /* Полупрозрачный фон для контейнеров */
    .element-container, .stMarkdown {
        background-color: rgba(0, 0, 0, 0.4);
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
    }
    /* Уменьшаем размер поля ввода города */
    .stTextInput > div > div > input {
        max-width: 300px;
    }
</style>
""", unsafe_allow_html=True)

if 'current_city' not in st.session_state:
    st.session_state.current_city = ""
if 'background_set' not in st.session_state:
    st.session_state.background_set = False

st.markdown("<h1 style='text-align: center; color: white; text-shadow: 2px 2px 4px black;'>Городская платформа</h1>",
            unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: white; text-shadow: 1px 1px 2px black;'>Введите город для получения информации:</p>",
    unsafe_allow_html=True)

# Ограничиваем поле ввода города 30 символами
city = st.text_input("", placeholder="Введите название города...", max_chars=30)

if city:
    # Генерируем уникальный ID для города на основе имени
    city_id = ''.join(c for c in city if c.isalnum()).lower()

    # Получаем данные о городе
    time_of_day = get_city_time_of_day(city)
    weather = get_weather(city)
    radio_data = get_radio(city)
    webcam_data = get_webcam_data(city)

    # Устанавливаем фон с веб-камерой
    webcam_url = webcam_data.get("webcam_url")
    if webcam_url:
        set_background(webcam_url)
        st.session_state.background_set = True

    # Отображаем информацию
    col1, col2 = st.columns([2, 1])

    with col1:
        if "error" not in weather:
            st.markdown(f"""
            <div style="color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">
                <h2>Погода в {city}</h2>
                <p><strong>Температура:</strong> {weather['temperature']}°C (ощущается как {weather['feels_like']}°C)</p>
                <p><strong>Погодные условия:</strong> {weather['weather']}</p>
                <p><strong>Влажность:</strong> {weather['humidity']}%</p>
                <p><strong>Скорость ветра:</strong> {weather['wind_speed']} м/с</p>
                <p><strong>Давление:</strong> {weather['pressure']} мм рт. ст.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Не удалось получить погоду для города {city}")

    with col2:
        if radio_data and "radio_url" in radio_data:
            radio_html = create_autoplay_radio(radio_data["radio_url"], city_id)
            html(radio_html, height=150)
        else:
            st.warning(f"Радиостанции для города {city} не найдены.")

    # Воспроизводим фоновые звуки
    ambient_sounds_js = play_ambient_sounds(time_of_day, city_id)
    if ambient_sounds_js:
        html(ambient_sounds_js, height=0)