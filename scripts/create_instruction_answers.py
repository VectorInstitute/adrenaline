"""Script to create instruction answers for EHR data."""

import os
from api.patients.ehr import (
    init_lazy_df,
    fetch_recent_encounter_events
)


MEDS_DATA_DIR = os.getenv(
    "MEDS_DATA_DIR", "/mnt/data/odyssey/meds/hosp/merge_to_MEDS_cohort/train"
)
init_lazy_df(MEDS_DATA_DIR)


events = fetch_recent_encounter_events(10000032)
events_str = ""
for event in events:
    event_type = event.code.split("//")[0]
    if event_type == "MEDICATION":
        medication = event.code.split("//")[1]
        events_str += f"{medication} \n"


print(events_str)



