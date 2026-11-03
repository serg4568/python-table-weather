from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timezone
import pytz


app = Flask(__name__)

# Список городов по умолчанию (можно расширять)
DEFAULT_CITIES = [
    {"name": "Минск, Беларусь",        "lat": 53.9006, "lon": 27.5590},
    {"name": "Будча, Беларусь",        "lat": 52.76, "lon": 26.84},
    {"name": "Боровляны, Беларусь",    "lat": 53.9995,"lon": 27.6809},
    {"name": "Брест, Беларусь",        "lat": 52.0976, "lon": 23.7341},
    {"name": "Гродно, Беларусь",       "lat": 53.6884, "lon": 23.8258},
    {"name": "Витебск, Беларусь",      "lat": 55.1904, "lon": 30.2049},
    {"name": "Могилёв, Беларусь",      "lat": 53.8945, "lon": 30.3307},
    {"name": "Гомель, Беларусь",       "lat": 52.4345, "lon": 30.9754},
    {"name": "Бобруйск, Беларусь",     "lat": 53.1384, "lon": 29.2214},
    {"name": "Москва, Россия",         "lat": 55.7558, "lon": 37.6173},
    {"name": "Санкт-Петербург, Россия","lat": 59.9343, "lon": 30.3351},
    {"name": "Киев, Украина",          "lat": 50.4501, "lon": 30.5234},
]


def geocode_city(city_name: str):
    """Геокодирование через бесплатный Open-Meteo Geocoding API"""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "ru",
        "format": "json"
    }
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data.get("results"):
            result = data["results"][0]
            return {
                "name": result.get("name", city_name),
                "lat": result["latitude"],
                "lon": result["longitude"],
                "country": result.get("country", ""),
                "admin1": result.get("admin1", ""),
            }
    except Exception as e:
        print(f"Ошибка геокодирования: {e}")
    return None

def model_upd(model):

    modelname=''
    if model=='icon_global':
        modelname='dwd_icon'
    elif model=='icon_eu':
        modelname='dwd_icon_eu'
    elif model=='gfs_seamless':
        modelname='ncep_gfs013'
    elif model=='metno_seamless':
        modelname='metno_nordic_pp'
    elif model=='ukmo_seamless':
        modelname='ukmo_global_deterministic_10km'
    elif model=='meteofrance_seamless':
        modelname='meteofrance_arpege_world025'
    elif model=='best_match':
        modelname='best_match'
    elif model=='gem_seamless':
        modelname='cmc_gem_gdps'
    elif model=='jma_seamless':
            modelname='jma_gsm'
    elif model=='jma_seamless':
                modelname='jma_gsm'
    elif model=='geosphere_seamless':
                    modelname='geosphere_arome_austria'
    elif model=='chmi_aladin_seamless':
                        modelname='chmi_aladin_central_europe_2km'
    elif model=='knmi_harmonie_arome_europe':
                            modelname='knmi_harmonie_arome_europe'                                 
    else:
        modelname=model
    try:
        upd_response=requests.get(f"https://api.open-meteo.com/data/{modelname}/static/meta.json").json()
        lastupd=upd_response.get('last_run_initialisation_time','-')
        given_dt = datetime.fromtimestamp(lastupd, tz=timezone.utc)
        resulution=upd_response.get('temporal_resolution_seconds',0)/3600
        update_int=upd_response.get('update_interval_seconds',0)/3600
        updstr=given_dt.strftime("%d-%m-%H")
        updstr=f"{model}:{updstr}Z, forecast resol: {round(resulution)}H, upd interval: {round(update_int)}H"
    except:
        updstr=''
    return updstr
def get_weather_data(lat: float, lon: float, resolution: str = "hourly_3", model: str = "best_match"):
    """Получаем данные с Open-Meteo Forecast API"""
    temporal_resolution = "hourly_3" if resolution == "hourly_3" else "hourly" #native в будущем

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": (
            "temperature_2m,temperature_850hPa,precipitation,total_column_integrated_water_vapour,"
            "weathercode,relative_humidity_2m,cloud_cover,"
            "wind_speed_10m,wind_direction_10m,"
            "cape,lifted_index,pressure_msl",
            "wind_direction_850hPa","wind_speed_850hPa","wind_speed_500hPa","wind_direction_500hPa","snow_depth"
        ),
        "forecast_days": 16,
        "models": model,
        "temporal_resolution": temporal_resolution,
        "timezone": "Europe/Minsk",
        
    }

    url = "https://api.open-meteo.com/v1/forecast"
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Ошибка получения погоды: {e}")
        return None


@app.route("/")
def index():
    return render_template("index.html", default_cities=DEFAULT_CITIES)


@app.route("/get_weather", methods=["POST"])
def get_weather():
    data = request.get_json()
    city_name = data.get("city", "").strip()
    lat = data.get("lat")
    lon = data.get("lon")
    resolution = data.get("resolution", "hourly_3")
    model = data.get("model", "best_match")


    # Если координаты не переданы — геокодируем город
    if not (lat and lon):
        geo = geocode_city(city_name)
        if not geo:
            return jsonify({"error": "Не удалось найти такой город"}), 400
        lat = geo["lat"]
        lon = geo["lon"]
        display_name = f"{geo['name']}, {geo.get('admin1', '')}, {geo.get('country', '')}".strip(", ")
    else:
        display_name = city_name or "Выбранное местоположение"

    weather_data = get_weather_data(lat, lon, resolution, model)
    if not weather_data or "hourly" not in weather_data:
        return jsonify({"error": "Не удалось получить данные о погоде"}), 500

    # Подготовка данных для фронтенда
    hourly = weather_data["hourly"]
    times = hourly["time"]
    result = []

    # Текущее время в часовом поясе прогноза
    tz = pytz.timezone(weather_data.get("timezone", "UTC"))
    now = datetime.now(tz)
    upd=model_upd(model)
    buf=0
    minsk_time_hour=datetime.now(pytz.timezone("Europe/Minsk")).hour
    if resolution=="hourly_3":
        buf2=minsk_time_hour//3
    else:
        buf2=minsk_time_hour-1
    if buf2<0:
        buf2=0
    for i, dt_str in enumerate(times):
        if i>=buf2:
            # Open-Meteo возвращает время в ISO с Z → преобразуем
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

            # Пропускаем прошедшие часы, если включена опция
            date_ru = dt.strftime("%a-%d %H:00")
            time_ru = dt.strftime("%H:00")
            temp = hourly["temperature_2m"][i]
            if temp==None:
                buf=buf+1
                if buf==2:
                    break
            temp850 = hourly.get("temperature_850hPa", [None] * len(times))[i]
            precip = hourly["precipitation"][i]
            pwat = hourly.get("total_column_integrated_water_vapour",None)[i]
            snow_d=round(hourly["snow_depth"][i]*100) if hourly["snow_depth"][i] is not None else "-"
            wind10 = hourly["wind_speed_10m"][i]
            wind850 = hourly["wind_speed_850hPa"][i]
            wind500=hourly.get("wind_speed_500hPa",'-')[i]
            wind_dir10 = hourly["wind_direction_10m"][i]
            wind_dir850 = hourly["wind_direction_850hPa"][i]
            wind_dir500=hourly.get("wind_direction_500hPa",'-')[i]
            rh = hourly["relative_humidity_2m"][i]
            weathercode = hourly["weathercode"][i]
            cape = hourly.get("cape", [None] * len(times))[i]
            li = hourly.get("lifted_index", [None] * len(times))[i]
            pressure = hourly.get("pressure_msl", [None] * len(times))[i]
            cloud_cover = hourly["cloud_cover"][i]


            result.append({
                "date": date_ru,
                #"time": time_ru,
                "temp": round(temp, 1) if temp is not None else None,
                "temp850": round(temp850, 1) if temp850 is not None else None,
                "precip": round(precip, 1) if precip is not None else None,
                "snow_d":snow_d,
                "wind10": round(wind10, 0) if wind10 is not None else None,
                "wind850": round(wind850, 0) if wind850 is not None else None,
                "wind500": round(wind500, 0) if wind500 is not None else None,
                "wind_dir10": wind_dir10,
                "wind_dir850": wind_dir850,
                "wind_dir500": wind_dir500,
                "rh": rh if rh is not None else None,
                "weathercode": weathercode,
                "pwat":round(pwat, 0) if pwat is not None else None,
                "cape": cape,
                "li": li,
                "pressure": round(pressure) if pressure is not None else None,
                "cloud_cover": cloud_cover,
            

        })

    return jsonify({
        "location": display_name,
        "timezone": weather_data.get("timezone", "UTC"),
        "data": result,
        "generation_time": weather_data.get("generationtime_ms"),
        "model_used": model,
        "updstr":upd,
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)