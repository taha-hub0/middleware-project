# Producer service: generate fake logs and POST to middleware.
import os
import random
import time

import requests
from faker import Faker


SCENARIO_CATALOG = [
    {
        "name": "login_success",
        "event_type": "login",
        "level": "INFO",
        "role": "web_dev",
        "message_hint": "successful login",
    },
    {
        "name": "logout_success",
        "event_type": "logout",
        "level": "INFO",
        "role": "system_admin",
        "message_hint": "user logout",
    },
    {
        "name": "payment_processed",
        "event_type": "payment",
        "level": "WARNING",
        "role": "cybersec",
        "message_hint": "payment processed",
    },
    {
        "name": "profile_update",
        "event_type": "profile_update",
        "level": "INFO",
        "role": "web_dev",
        "message_hint": "profile update",
    },
    {
        "name": "login_failed",
        "event_type": "login_failed",
        "level": "ERROR",
        "role": "cybersec",
        "message_hint": "failed login",
    },
    {
        "name": "critical_alert",
        "event_type": "payment",
        "level": "CRITICAL",
        "role": "system_admin",
        "message_hint": "critical payment alert",
    },
]


def build_record(scenario: dict | None = None) -> dict:
    faker = Faker()
    scenario = scenario or {}
    message_hint = str(scenario.get("message_hint", "log event"))
    return {
        "timestamp": faker.iso8601(),
        "scenario": scenario.get("name", "random"),
        "level": scenario.get("level", random.choice(["INFO", "WARNING", "ERROR", "CRITICAL", "DEBUG"])),
        "event_type": scenario.get(
            "event_type",
            random.choice(["login", "logout", "payment", "profile_update", "login_failed"]),
        ),
        "role": scenario.get("role", random.choice(["system_admin", "cybersec", "web_dev"])),
        "message": f"{message_hint}: {faker.sentence(nb_words=6)}",
        "user_name": faker.name(),
        "email": faker.email(),
        "phone": faker.phone_number(),
        "ip": faker.ipv4(),
        # Turkish national id / tracking code - 11 digits similar to stress_test
        "tc": "".join(str(random.randint(0, 9)) for _ in range(11)),
        # credit card number for payment scenarios
        "credit_card": faker.credit_card_number(card_type=None),
    }


def iter_scenarios(count: int) -> list[dict]:
    if count <= 0:
        return []
    return [SCENARIO_CATALOG[index % len(SCENARIO_CATALOG)] for index in range(count)]


def send_record(record: dict, endpoint: str) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            response = requests.post(endpoint, json=record, timeout=10)
            response.raise_for_status()
            return
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 30:
                break
            time.sleep(1)
    if last_error is not None:
        raise last_error


def main() -> None:
    endpoint = os.getenv("MIDDLEWARE_URL", "http://localhost:8000/logs")
    count = int(os.getenv("PRODUCER_COUNT", "5"))
    delay = float(os.getenv("PRODUCER_DELAY", "0.5"))
    for scenario in iter_scenarios(count):
        record = build_record(scenario)
        send_record(record, endpoint)
        time.sleep(delay)


if __name__ == "__main__":
    main()
