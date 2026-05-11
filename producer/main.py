# Producer service: generate fake logs and POST to middleware.
import os
import random
import time

import requests
from faker import Faker


def build_record() -> dict:
    faker = Faker()
    levels = ["INFO", "WARNING", "ERROR", "CRITICAL", "DEBUG"]
    event_types = ["login", "logout", "payment", "profile_update", "login_failed"]
    return {
        "timestamp": faker.iso8601(),
        "level": random.choice(levels),
        "event_type": random.choice(event_types),
        "message": faker.sentence(nb_words=6),
        "user_name": faker.name(),
        "email": faker.email(),
        "phone": faker.phone_number(),
        "ip": faker.ipv4(),
    }


def send_record(record: dict, endpoint: str) -> None:
    response = requests.post(endpoint, json=record, timeout=10)
    response.raise_for_status()


def main() -> None:
    endpoint = os.getenv("MIDDLEWARE_URL", "http://localhost:8000/logs")
    count = int(os.getenv("PRODUCER_COUNT", "5"))
    delay = float(os.getenv("PRODUCER_DELAY", "0.5"))
    for _ in range(count):
        record = build_record()
        send_record(record, endpoint)
        time.sleep(delay)


if __name__ == "__main__":
    main()
