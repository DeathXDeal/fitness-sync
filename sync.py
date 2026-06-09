import requests
import json
import os
from datetime import datetime

HEVY_API_KEY = os.environ['HEVY_API_KEY']
BASE_URL = "https://api.hevyapp.com/v1"
headers = {"api-key": HEVY_API_KEY}

def get_workouts():
    response = requests.get(
        f"{BASE_URL}/workouts",
        headers=headers,
        params={"page": 1, "pageSize": 5}
    )
    response.raise_for_status()
    return response.json()

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

def main():
    data = get_workouts()
    workouts = data.get('workouts', [])
    output = {
        "last_updated": datetime.utcnow().isoformat(),
        "workouts": [format_workout(w) for w in workouts]
    }
    os.makedirs('data', exist_ok=True)
    with open('data/hevy_latest.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(workouts)} workouts")

if __name__ == "__main__":
    main()
