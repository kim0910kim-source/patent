#!/usr/bin/env python3
"""BigQuery 공개 특허 데이터셋으로 전력반도체 기업의 US 특허 규모를 집계한다.

사전 준비 (둘 중 하나):
  1) 서비스 계정 키:  export GOOGLE_APPLICATION_CREDENTIALS=/path/key.json
  2) 사용자 인증:     gcloud auth application-default login
그리고 과금 프로젝트:  export GOOGLE_CLOUD_PROJECT=<your-project-id>

실행:  python3 bigquery/run_power_device_query.py [--dry-run]
결과:  reports/bigquery_power_device_us_patents.md (마크다운 표) 및 .csv
"""
import csv
import os
import sys
from pathlib import Path

from google.cloud import bigquery

ROOT = Path(__file__).resolve().parent.parent
SQL_PATH = ROOT / "bigquery" / "power_device_us_patents.sql"
OUT_MD = ROOT / "reports" / "bigquery_power_device_us_patents.md"
OUT_CSV = ROOT / "reports" / "bigquery_power_device_us_patents.csv"


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        print("GOOGLE_CLOUD_PROJECT 환경변수(과금 프로젝트 ID)가 필요합니다.", file=sys.stderr)
        return 2

    client = bigquery.Client(project=project)
    sql = SQL_PATH.read_text(encoding="utf-8")
    job_config = bigquery.QueryJobConfig(dry_run=dry_run, use_query_cache=True)
    job = client.query(sql, job_config=job_config)

    if dry_run:
        gb = job.total_bytes_processed / 1e9
        print(f"스캔 예상량: {gb:,.1f} GB (온디맨드 요금 기준 약 ${gb / 1000 * 6.25:.2f})")
        return 0

    rows = list(job.result())
    if not rows:
        print("결과 없음", file=sys.stderr)
        return 1

    cols = list(rows[0].keys())
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])

    lines = ["# BigQuery 집계: 전력반도체 기업 US 등록특허", "",
             f"데이터셋: `patents-public-data.patents.publications`, 잡 ID: `{job.job_id}`", "",
             "| " + " | ".join(cols) + " |",
             "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n저장: {OUT_MD}, {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
