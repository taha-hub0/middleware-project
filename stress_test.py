# Simple stress test script for the middleware API.
# Bu dosya: eşzamanlı isteklerle `middleware` performansını ölçer. `producer` yerine doğrudan
# HTTP POST istekleri gönderir; sonuçları Req/s, Processed, Dropped ve Errors olarak raporlar.
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import requests
from faker import Faker


ENDPOINT = os.getenv("MIDDLEWARE_URL", "http://127.0.0.1:8000/logs")
DEFAULT_COUNTS = [100, 1000, 5000]
# Varsayılan eşikte (WARNING) log_filter_step'ten geçen seviyeler. Böylece test maskeleme,
# zenginleştirme, formatlama ve dosya yazma dahil tüm pipeline'ı ölçer (bkz. middleware/steps.py).
# LOG_LEVEL_THRESHOLD yükseltilirse aşağıdaki kayıtlar Dropped olarak raporlanır.
LEVELS = ["WARNING", "ERROR", "CRITICAL"]
EVENT_TYPES = ["login_failed", "payment", "logout", "profile_update"]
ROLES = ["system_admin", "cybersec", "web_dev"]
DEFAULT_WORKERS = 32


@dataclass
class TestResult:
    request_count: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    processed_count: int
    dropped_count: int
    error_count: int
    requests_per_second: float

    @property
    def success_count(self) -> int:
        return self.processed_count + self.dropped_count


def generate_tc(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(11))


def build_payload(seq_id: int, faker: Faker, rng: random.Random) -> dict:
    # Alan adları middleware'in beklediği şema ile aynı olmalı (bkz. producer/main.py):
    # `level` filtreyi, `event_type` zenginleştirmeyi, `role` format sırasını belirler.
    return {
        "id": seq_id,
        "timestamp": faker.iso8601(),
        "level": rng.choice(LEVELS),
        "event_type": rng.choice(EVENT_TYPES),
        "role": rng.choice(ROLES),
        "message": faker.sentence(nb_words=6),
        "user_name": faker.name(),
        "email": faker.email(),
        "phone": faker.phone_number(),
        "ip": faker.ipv4(),
        "tc": generate_tc(rng),
        "credit_card": faker.credit_card_number(card_type=None),
    }


def post_payload(endpoint: str, payload: dict, timeout: int = 10) -> str:
    # Dönen değer: "processed", "dropped" veya "error".
    # Middleware filtrelenen kayda da 200 döndüğü için durum gövdeden okunur.
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
        if not response.ok:
            return "error"
        if response.json().get("status") == "dropped":
            return "dropped"
        return "processed"
    except (requests.RequestException, ValueError):
        return "error"


def run_single_test(
    request_count: int,
    endpoint: str = ENDPOINT,
    verbose: bool = False,
    max_workers: int = DEFAULT_WORKERS,
) -> TestResult:
    faker = Faker()
    rng = random.Random()

    worker_count = max(1, min(max_workers, request_count))
    # Payload üretimi ölçümün dışında tutulur; aksi halde Faker'ın maliyeti Req/s'e yazılır.
    payloads = [build_payload(index, faker, rng) for index in range(1, request_count + 1)]

    start_time = datetime.now()
    start_perf = time.perf_counter()

    processed_count = 0
    dropped_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(post_payload, endpoint, payload): index
            for index, payload in enumerate(payloads, start=1)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                outcome = future.result()
            except Exception as exc:  # pragma: no cover - defensive guard for worker failures
                error_count += 1
                if verbose:
                    print(f"[ERROR] {index} -> {exc}")
                continue
            if outcome == "processed":
                processed_count += 1
            elif outcome == "dropped":
                dropped_count += 1
                if verbose:
                    print(f"[WARN] {index} -> dropped by filter")
            else:
                error_count += 1
                if verbose:
                    print(f"[WARN] {index} -> request failed")

    end_perf = time.perf_counter()
    end_time = datetime.now()

    duration_seconds = end_perf - start_perf
    completed_count = processed_count + dropped_count
    requests_per_second = (
        completed_count / duration_seconds if duration_seconds > 0 else 0.0
    )

    return TestResult(
        request_count=request_count,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        processed_count=processed_count,
        dropped_count=dropped_count,
        error_count=error_count,
        requests_per_second=requests_per_second,
    )


def run_tests(
    counts: Iterable[int] = DEFAULT_COUNTS,
    endpoint: str = ENDPOINT,
    max_workers: int = DEFAULT_WORKERS,
) -> None:
    results = [
        run_single_test(count, endpoint=endpoint, max_workers=max_workers)
        for count in counts
    ]
    print("\nStress Test Results")
    print("-" * 70)
    for result in results:
        print(
            f"Requests: {result.request_count} | "
            f"Start: {result.start_time:%H:%M:%S} | "
            f"End: {result.end_time:%H:%M:%S}"
        )
        print(
            f"Duration: {result.duration_seconds:.2f}s | "
            f"Req/s: {result.requests_per_second:.2f} | "
            f"Processed: {result.processed_count} | "
            f"Dropped: {result.dropped_count} | "
            f"Errors: {result.error_count}"
        )
        print("-" * 70)
    total_files = sum(result.processed_count for result in results) * 3
    print(f"Note: each processed record writes 3 files -> ~{total_files} files in outputs/")


def main() -> None:
    run_tests()


if __name__ == "__main__":
    main()
