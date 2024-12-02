"""Script to create instruction answers for EHR data."""

import os
from api.patients.ehr import init_lazy_df, fetch_latest_medications


MEDS_DATA_DIR = os.getenv("MEDS_DATA_DIR", "/Volumes/clinical-data/train")
init_lazy_df(MEDS_DATA_DIR)


meds = fetch_latest_medications(10000032)
print(meds)
