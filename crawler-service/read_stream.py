#!/usr/bin/env python3
"""
read_stream.py — monitor the jobs:raw Redis Stream in real time.

Usage:
    python read_stream.py              # tail new events continuously
    python read_stream.py --all        # dump everything in the stream
    python read_stream.py --count 20   # show last 20 entries
"""
import json
import time
import argparse
import redis


def tail_stream(r: redis.Redis, stream_key: str, last_id: str = "$"):
    print(f"\nTailing '{stream_key}' — waiting for new jobs...\n")
    while True:
        results = r.xread({stream_key: last_id}, count=10, block=2000)
        if not results:
            continue
        for _, messages in results:
            for msg_id, data in messages:
                last_id = msg_id
                print_job(msg_id, data)


def dump_stream(r: redis.Redis, stream_key: str, count: int):
    entries = r.xrevrange(stream_key, count=count)
    if not entries:
        print(f"Stream '{stream_key}' is empty. Run a spider first.")
        return
    print(f"\n{len(entries)} most recent jobs in '{stream_key}':\n")
    for msg_id, data in reversed(entries):
        print_job(msg_id, data)


def print_job(msg_id: str, data: dict):
    stack = json.loads(data.get("stack", "[]"))
    stack_str = ", ".join(stack[:5]) or "—"
    print(
        f"  [{msg_id}]\n"
        f"  Company  : {data.get('company')}\n"
        f"  Role     : {data.get('role')}\n"
        f"  Stack    : {stack_str}\n"
        f"  Source   : {data.get('source')}\n"
        f"  URL      : {data.get('url')}\n"
        f"  Posted   : {data.get('posted_at')}\n"
        f"  {'─' * 60}\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",   action="store_true", help="Dump full stream")
    parser.add_argument("--count", type=int, default=20, help="How many entries to show")
    parser.add_argument("--host",  default="localhost")
    parser.add_argument("--port",  type=int, default=6379)
    args = parser.parse_args()

    r = redis.Redis(host=args.host, port=args.port, decode_responses=True)

    try:
        r.ping()
    except redis.ConnectionError:
        print(f"Cannot connect to Redis at {args.host}:{args.port}. Is it running?")
        raise SystemExit(1)

    if args.all or args.count:
        dump_stream(r, "jobs:raw", args.count)
    else:
        tail_stream(r, "jobs:raw", last_id="$")
