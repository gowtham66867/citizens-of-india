import os

try:
    from google.cloud import bigquery as _bq
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False

_client = None

DEMOGRAPHICS = {
    "default": {
        "constituency": "Demo Constituency",
        "population": 250000,
        "rural_pct": 65,
        "literacy_rate": 72,
        "below_poverty_line_pct": 18,
        "primary_occupation": "Agriculture",
        "households": 48000,
    }
}


def get_demographics(constituency: str) -> dict:
    if not _AVAILABLE or not os.environ.get("GCP_PROJECT_ID"):
        return DEMOGRAPHICS["default"]
    global _client
    try:
        if _client is None:
            _client = _bq.Client(project=os.environ["GCP_PROJECT_ID"])
        query = f"""
            SELECT *
            FROM `{os.environ['GCP_PROJECT_ID']}.constituency_data.demographics`
            WHERE constituency_name = @constituency
            LIMIT 1
        """
        job_config = _bq.QueryJobConfig(
            query_parameters=[_bq.ScalarQueryParameter("constituency", "STRING", constituency)]
        )
        results = list(_client.query(query, job_config=job_config).result())
        if results:
            return dict(results[0])
    except Exception:
        pass
    return DEMOGRAPHICS["default"]
