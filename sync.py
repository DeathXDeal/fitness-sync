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
    headers = {"Authorization": f"Bearer {token}"}
    today = datetime.utcnow().strftime("%Y-%m-%d")

    activity = requests.get(
        f"https://health.googleapis.com/v4/users/-/activities/date/{today}",
        headers=headers
    ).json()

    sleep = requests.get(
        f"https://health.googleapis.com/v4/users/-/sleep/date/{today}",
        headers=headers
    ).json()

    return {
        "date": today,
        "steps": activity.get("summary", {}).get("steps", 0),
        "calories_burnt": activity.get("summary", {}).get("caloriesOut", 0),
        "sleep_hours": round(sleep.get("summary", {}).get("totalMinutesAsleep", 0) / 60, 1)
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
