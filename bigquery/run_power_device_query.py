#!/usr/bin/env python3
"""BigQuery 공개 특허 데이터셋으로 전력반도체 기업의 US 특허 규모를 집계한다.

사전 준비: 과금 프로젝트 ID  GOOGLE_CLOUD_PROJECT=<project-id>
인증 (아래 중 하나, 위에서부터 우선):
  1) GCP_SA_KEY_B64   : 서비스 계정 키 JSON을 base64 한 줄로 (Claude Code 클라우드 환경변수용)
  2) GCP_SA_KEY_JSON  : 서비스 계정 키 JSON 원문 (따옴표로 감싸 여러 줄 허용)
  3) GOOGLE_APPLICATION_CREDENTIALS=/path/key.json  또는  gcloud auth application-default login

실행:  python3 bigquery/run_power_device_query.py [--dry-run]
결과:  reports/bigquery_power_device_us_patents.md (마크다운 표) 및 .csv
"""
import base64
import csv
import os
import stat
import sys
import tempfile
from pathlib import Path

from google.cloud import bigquery

ROOT = Path(__file__).resolve().parent.parent
SQL_PATH = ROOT / "bigquery" / "power_device_us_patents.sql"
OUT_MD = ROOT / "reports" / "bigquery_power_device_us_patents.md"
OUT_CSV = ROOT / "reports" / "bigquery_power_device_us_patents.csv"


def materialize_credentials() -> None:
    """환경변수에 담긴 서비스 계정 키를 임시 파일로 풀어 ADC로 등록한다."""
    raw = None
    if os.environ.get("GCP_SA_KEY_B64"):
        raw = base64.b64decode(os.environ["GCP_SA_KEY_B64"].strip())
    elif os.environ.get("GCP_SA_KEY_JSON"):
        raw = os.environ["GCP_SA_KEY_JSON"].encode("utf-8")
    if raw is None:
        return
    fd, path = tempfile.mkstemp(prefix="gcp-sa-", suffix=".json")
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    materialize_credentials()
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
