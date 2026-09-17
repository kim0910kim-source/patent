-- 전력반도체 주요 기업의 US 등록특허 규모 (Google BigQuery 공개 데이터셋 patents-public-data)
-- 실행: bq query --use_legacy_sql=false < bigquery/power_device_us_patents.sql
--       또는 python3 bigquery/run_power_device_query.py
--
-- 집계 정의
--   us_granted_total     : US 등록특허(B1/B2) 전체, 전 기간
--   us_granted_active    : 등록일 2006-01-01 이후 (20년 존속기간 근사, 유지료 미납 소멸은 미반영)
--   power_device_*       : CPC H10D(2025년 신설, 구 H01L29 등 반도체 소자) 또는 H01L29 포함 특허
--   power_device_2021..2025 : 연도별 등록 건수 (소자 한정)
--
-- 주의: assignee_harmonized 이름 정규식 매칭이므로 계열사/구사명 누락·오포함 가능.
--       필요 시 아래 company_map 정규식을 조정.

WITH company_map AS (
  SELECT * FROM UNNEST([
    STRUCT('onsemi'              AS company, r'^(SEMICONDUCTOR COMPONENTS IND|ON SEMICONDUCTOR|FAIRCHILD SEMICONDUCTOR)' AS pattern),
    STRUCT('STMicroelectronics'  AS company, r'^STMICROELECTRONICS' AS pattern),
    STRUCT('ROHM'                AS company, r'^ROHM (CO|SEMICONDUCTOR)' AS pattern),
    STRUCT('Infineon'            AS company, r'^(INFINEON|INTERNATIONAL RECTIFIER|CYPRESS SEMICONDUCTOR)' AS pattern),
    STRUCT('Wolfspeed'           AS company, r'^(WOLFSPEED|CREE INC|CREE,? INC)' AS pattern),
    STRUCT('Toshiba'             AS company, r'^(TOSHIBA|KABUSHIKI KAISHA TOSHIBA)' AS pattern),
    STRUCT('Sumitomo Electric'   AS company, r'^SUMITOMO ELECTRIC' AS pattern),
    STRUCT('Mitsubishi Electric' AS company, r'^MITSUBISHI ELECTRIC' AS pattern),
    STRUCT('Toyota'              AS company, r'^TOYOTA (MOTOR|JIDOSHA|CENTRAL)' AS pattern),
    STRUCT('Denso'               AS company, r'^DENSO' AS pattern),
    STRUCT('Fuji Electric'       AS company, r'^FUJI ELECTRIC' AS pattern)
  ])
),
us_grants AS (
  SELECT
    p.publication_number,
    p.grant_date,
    CAST(FLOOR(p.grant_date / 10000) AS INT64) AS grant_year,
    EXISTS (
      SELECT 1 FROM UNNEST(p.cpc) c
      WHERE REGEXP_CONTAINS(c.code, r'^(H10D|H01L29)')
    ) AS is_power_device,
    ARRAY(SELECT DISTINCT UPPER(a.name) FROM UNNEST(p.assignee_harmonized) a) AS assignee_names
  FROM `patents-public-data.patents.publications` p
  WHERE p.country_code = 'US'
    AND p.kind_code IN ('B1', 'B2')
    AND p.grant_date > 0
),
matched AS (
  SELECT DISTINCT
    m.company,
    g.publication_number,
    g.grant_date,
    g.grant_year,
    g.is_power_device
  FROM us_grants g
  CROSS JOIN UNNEST(g.assignee_names) AS name
  JOIN company_map m ON REGEXP_CONTAINS(name, m.pattern)
)
SELECT
  company,
  COUNT(*)                                                        AS us_granted_total,
  COUNTIF(grant_date >= 20060101)                                 AS us_granted_active,
  COUNTIF(is_power_device)                                        AS power_device_total,
  COUNTIF(is_power_device AND grant_date >= 20060101)             AS power_device_active,
  COUNTIF(is_power_device AND grant_year = 2021)                  AS power_device_2021,
  COUNTIF(is_power_device AND grant_year = 2022)                  AS power_device_2022,
  COUNTIF(is_power_device AND grant_year = 2023)                  AS power_device_2023,
  COUNTIF(is_power_device AND grant_year = 2024)                  AS power_device_2024,
  COUNTIF(is_power_device AND grant_year = 2025)                  AS power_device_2025,
  COUNTIF(grant_year = 2025)                                      AS us_granted_2025
FROM matched
GROUP BY company
ORDER BY power_device_active DESC;
