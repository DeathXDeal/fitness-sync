import requests
import json
import os
from datetime import datetime

HEVY_API_KEY = os.environ['HEVY_API_KEY']
BASE_URL = "https://api.hevyapp.com/v1"
hevy_headers = {"api-key": HEVY_API_KEY}

def get_all_workouts():
    all_workouts = []
    page = 1
    while True:
        response = requests.get(
            f"{BASE_URL}/workouts",
            headers=hevy_headers,
            params={"page": page, "pageSize": 10}
        )
        if response.status_code == 404:
            break
        response.raise_for_status()
        data = response.json()
        batch = data.get('workouts', [])
        if not batch:
            break
        all_workouts.extend(batch)
        page += 1
    return all_workouts

def format_workout(workout):
    exercises = []
    for exercise in workout.get('exercises', []):
        sets = []
        for s in exercise.get('sets', []):
            sets.append({
                "set_type": s.get('set_type'),
                "reps": s.get('reps'),
                "weight_kg": s.get('weight_kg')
            })
        exercises.append({
            "title": exercise.get('title'),
            "sets": sets
        })
    return {
        "title": workout.get('title'),
        "start_time": workout.get('start_time'),
        "end_time": workout.get('end_time'),
        "exercises": exercises
    }

def get_google_token():
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"
    })
    return resp.json()["access_token"]

def get_fitbit_data():
    token = get_google_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    today = datetime.utcnow()
    date_str = today.strftime("%Y-%m-%d")

    steps_payload = {
        "range": {
            "start": {
                "date": {"year": today.year, "month": today.month, "day": today.day},
                "time": {"hours": 0, "minutes": 0, "seconds": 0, "nanos": 0}
            },
            "end": {
                "date": {"year": today.year, "month": today.month, "day": today.day},
                "time": {"hours": 23, "minutes": 59, "seconds": 59, "nanos": 0}
            }
        },
        "windowSizeDays": 1
    }
    steps_resp = requests.post(
        "https://health.googleapis.com/v4/users/me/dataTypes/steps/dataPoints:dailyRollUp",
        headers=headers, json=steps_payload
    )
    steps_data = steps_resp.json()
    steps = 0
# Calories burned
    calories_payload = {
        "range": {
            "start": {
                "date": {"year": today.year, "month": today.month, "day": today.day},
                "time": {"hours": 0, "minutes": 0, "seconds": 0, "nanos": 0}
            },
            "end": {
                "date": {"year": today.year, "month": today.month, "day": today.day},
                "time": {"hours": 23, "minutes": 59, "seconds": 59, "nanos": 0}
            }
        },
        "windowSizeDays": 1
    }
    calories_resp = requests.post(
        "https://health.googleapis.com/v4/users/me/dataTypes/calories.expended/dataPoints:dailyRollUp",
        headers=headers, json=calories_payload
    )
    calories_data = calories_resp.json()
    print("CALORIES RAW:", json.dumps(calories_data))  # DEBUG

    calories = 0
    if calories_data.get("rollupDataPoints"):
        calories = round(calories_data["rollupDataPoints"][0].get("calories.expended", {}).get("fpSum", 0))
    
    if steps_data.get("rollupDataPoints"):
        steps = int(steps_data["rollupDataPoints"][0].get("steps", {}).get("countSum", 0))

    sleep_url = f"https://health.googleapis.com/v4/users/me/dataTypes/sleep/dataPoints:reconcile?filter=sleep.interval.civil_end_time >= \"{date_str}\""
    sleep_resp = requests.get(sleep_url, headers=headers)
    sleep_data = sleep_resp.json()
    sleep_hours = 0
    if sleep_data.get("dataPoints"):
        minutes = int(sleep_data["dataPoints"][0].get("sleep", {}).get("summary", {}).get("minutesAsleep", 0))
        sleep_hours = round(minutes / 60, 1)

    return {
        "date": date_str,
        "steps": steps,
        "calories_burnt": calories,
        "sleep_hours": sleep_hours
    }

def main():
    workouts = get_all_workouts()
    try:
        fitbit = get_fitbit_data()
    except Exception as e:
        fitbit = {"error": str(e)}

    output = {
        "last_updated": datetime.utcnow().isoformat(),
        "total_workouts": len(workouts),
        "fitbit_today": fitbit,
        "workouts": [format_workout(w) for w in workouts]
    }

    os.makedirs('data', exist_ok=True)
    with open('data/hevy_latest.json', 'w') as f:
        json.dump(output, f, indent=2)
    dated = datetime.utcnow().strftime('%Y-%m-%d')
    with open(f'data/hevy_{dated}.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(workouts)} workouts + Fitbit: {fitbit}")

if __name__ == "__main__":
    main()
