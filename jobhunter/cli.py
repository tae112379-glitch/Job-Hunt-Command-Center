"""사용: python -m jobhunter.cli collect-file data/sample_jobs.json | collect-rss URL | serve"""
import sys
from . import collectors


def main(argv=None):
    a = argv or sys.argv[1:]
    if not a:
        print(__doc__); return 1
    if a[0] == "collect-file":
        print(collectors.ingest(collectors.from_json_file(a[1]), min_score=10))
    elif a[0] == "collect-rss":
        print(collectors.ingest(collectors.from_rss(a[1]), min_score=10))
    elif a[0] == "serve":
        import uvicorn
        uvicorn.run("jobhunter.api:app", host="0.0.0.0", port=int(a[1]) if len(a) > 1 else 8000)
    else:
        print(__doc__); return 1


if __name__ == "__main__":
    main()
