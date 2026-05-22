# Simple stress test script for the middleware API.
import random
import time
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import requests
from faker import Faker


ENDPOINT = "http://127.0.0.1:8000/logs"
DEFAULT_COUNTS = [100, 1000, 5000]
LEVELS = ["info", "warning", "critical"]
DEPARTMENTS = ["DEV", "SYS", "GUV", "YON"]
DEFAULT_WORKERS = 32


@dataclass
class TestResult:
    request_count: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    success_count: int
    error_count: int
    requests_per_second: float


def generate_tc(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(11))


def build_payload(seq_id: int, faker: Faker, rng: random.Random) -> dict:
    return {
        "id": seq_id,
        "tc": generate_tc(rng),
        "isim": faker.name(),
        "mesaj": faker.sentence(nb_words=6),
        "seviye": rng.choice(LEVELS),
        "departman": rng.choice(DEPARTMENTS),
    }


def post_payload(endpoint: str, payload: dict, timeout: int = 10) -> bool:
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
        return response.ok
    except requests.RequestException:
        return False


def run_single_test(
    request_count: int,
    endpoint: str = ENDPOINT,
    verbose: bool = False,
    max_workers: int = DEFAULT_WORKERS,
) -> TestResult:
    faker = Faker()
    rng = random.Random()

    start_time = datetime.now()
    start_perf = time.perf_counter()

    success_count = 0
    error_count = 0

    worker_count = max(1, min(max_workers, request_count))
    payloads = [build_payload(index, faker, rng) for index in range(1, request_count + 1)]

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(post_payload, endpoint, payload): index
            for index, payload in enumerate(payloads, start=1)
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    error_count += 1
                    if verbose:
                        print(f"[WARN] {index} -> request failed")
            except Exception as exc:  # pragma: no cover - defensive guard for worker failures
                error_count += 1
                if verbose:
                    print(f"[ERROR] {index} -> {exc}")

    end_perf = time.perf_counter()
    end_time = datetime.now()

    duration_seconds = end_perf - start_perf
    requests_per_second = (
        success_count / duration_seconds if duration_seconds > 0 else 0.0
    )

    return TestResult(
        request_count=request_count,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        success_count=success_count,
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
            f"OK: {result.success_count} | "
            f"Errors: {result.error_count}"
        )
        print("-" * 70)


def main() -> None:
    run_tests()


if __name__ == "__main__":
    main()
