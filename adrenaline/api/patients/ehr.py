"""A module for loading EHR data from parquet files in MEDS format."""

import logging
import os
from typing import List, Optional

import polars as pl

from api.patients.data import Event


# Configure logging with a consistent format
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class EHRDataManager:
    """A class to manage EHR data using Polars LazyFrames for optimal performance."""

    def __init__(self) -> None:
        self.lazy_df: Optional[pl.LazyFrame] = None
        self._required_columns = {
            "patient_id",
            "encounter_id",
            "code",
            "description",
            "timestamp",
            "numeric_value",
            "text_value",
        }

    def init_lazy_df(self, directory: str) -> None:
        """Initialize the LazyFrame with the given directory.

        Parameters
        ----------
        directory : str
            The directory containing the MEDS parquet files.
        """
        if self.lazy_df is None:
            try:
                self.lazy_df = pl.scan_parquet(
                    os.path.join(directory, "*.parquet"), cache=True
                )

                # Ensure consistent column naming
                self.lazy_df = self.lazy_df.rename(
                    {
                        "subject_id": "patient_id",
                        "hadm_id": "encounter_id",
                        "time": "timestamp",
                    }
                )
                schema = set(self.lazy_df.collect_schema().names())
                missing_columns = self._required_columns - schema
                if missing_columns:
                    raise ValueError(f"Missing required columns: {missing_columns}")

                logger.info("LazyFrame initialized successfully")

            except Exception:
                logger.error("LazyFrame initialization failed", exc_info=True)
                raise

    def _process_event(self, event_data: dict) -> dict:
        """Process event data to extract event_type, environment, and details."""
        code_parts = event_data["code"].split("//")

        # Process event_type and environment
        if len(code_parts) > 1 and code_parts[0] in ["HOSPITAL", "ICU"]:
            environment = code_parts[0]
            event_type = code_parts[1]
        else:
            environment = None
            event_type = code_parts[0]

        # Process details based on event type
        if event_type in ["MEDICATION", "GENDER"]:
            if event_type == "GENDER":
                details = code_parts[1]
            else:
                details = ", ".join(code_parts[2:])
        else:
            details = event_data["description"]

        return {
            **event_data,
            "event_type": event_type,
            "environment": environment,
            "details": details,
        }

    def fetch_patient_events(self, patient_id: int) -> List[Event]:
        """Fetch all events for a patient.

        Parameters
        ----------
        patient_id : int
            The patient ID.

        Returns
        -------
        List[Event]
            List of events for the patient.
        """
        if self.lazy_df is None:
            raise ValueError("LazyFrame not initialized")

        try:
            filtered_df = (
                self.lazy_df.filter(pl.col("patient_id") == patient_id)
                .select(list(self._required_columns))
                .collect(streaming=True)
            )

            # Process each event
            processed_events = [
                self._process_event(row) for row in filtered_df.to_dicts()
            ]
            return [Event(**event) for event in processed_events]
        except Exception:
            logger.error(
                f"Error fetching events for patient {patient_id}", exc_info=True
            )
            raise

    def fetch_recent_encounter_events(self, patient_id: int) -> List[Event]:
        """Fetch events from most recent encounter with optimized query."""
        if self.lazy_df is None:
            raise ValueError("LazyFrame not initialized")

        try:
            # Optimize query by combining operations
            events_df = (
                self.lazy_df.filter(pl.col("patient_id") == patient_id)
                .sort("timestamp", descending=True)
                .group_by("encounter_id")
                .agg(
                    [
                        pl.first("timestamp").alias("latest_timestamp"),
                        pl.all().exclude(["timestamp"]),
                    ]
                )
                .limit(1)
                .explode(list(self._required_columns - {"timestamp"}))
                .collect(streaming=True)
            )

            if events_df.height == 0:
                logger.info(f"No encounters found for patient {patient_id}")
                return []

            return [Event(**row) for row in events_df.to_dicts()]
        except Exception:
            logger.error(
                f"Error fetching recent events for patient {patient_id}", exc_info=True
            )
            raise

    def fetch_patient_events_by_type(
        self, patient_id: int, event_type: str
    ) -> List[Event]:
        """Fetch events filtered by event_type for a patient."""
        if self.lazy_df is None:
            raise ValueError("LazyFrame not initialized")

        try:
            filtered_df = (
                self.lazy_df.filter(pl.col("patient_id") == patient_id)
                .select(list(self._required_columns))
                .collect(streaming=True)
            )

            # Process each event and filter by event_type
            processed_events = [
                self._process_event(row)
                for row in filtered_df.to_dicts()
                if self._process_event(row)["event_type"] == event_type
            ]
            return [Event(**event) for event in processed_events]
        except Exception:
            logger.error(
                f"Error fetching events for patient {patient_id}", exc_info=True
            )
            raise

    def fetch_latest_medications(self, patient_id: int) -> str:
        """Fetch medication events from the latest encounter and format them.

        Parameters
        ----------
        patient_id : int
            The patient ID.

        Returns
        -------
        str
            Comma-separated list of medications from the latest encounter.
        """
        if self.lazy_df is None:
            raise ValueError("LazyFrame not initialized")

        try:
            # First get all events for the patient
            filtered_df = (
                self.lazy_df.filter(pl.col("patient_id") == patient_id)
                .select(list(self._required_columns))
                .collect(streaming=True)
            )

            if filtered_df.height == 0:
                logger.info(f"No events found for patient {patient_id}")
                return ""

            # Process all events first
            processed_events = [
                self._process_event(row) for row in filtered_df.to_dicts()
            ]

            # Find the latest encounter
            latest_encounter = None
            latest_timestamp = None

            for event in processed_events:
                if event["event_type"] == "HOSPITAL_ADMISSION" and (
                    latest_timestamp is None or event["timestamp"] > latest_timestamp
                ):
                    latest_timestamp = event["timestamp"]
                    latest_encounter = event["encounter_id"]

            if latest_encounter is None:
                logger.info(f"No hospital admissions found for patient {patient_id}")
                return ""

            # Filter medications for the latest encounter
            medications = {
                event["details"]
                for event in processed_events
                if (
                    event["event_type"] == "MEDICATION"
                    and event["encounter_id"] == latest_encounter
                )
            }

            # Return sorted, comma-separated string
            return ", ".join(sorted(medications))

        except Exception as e:
            logger.error(
                f"Error fetching medications for patient {patient_id}: {str(e)}",
                exc_info=True,
            )
            raise


def fetch_patient_encounters(patient_id: int) -> List[dict]:
    """Fetch encounters with admission dates for a patient.

    Parameters
    ----------
    patient_id : int
        The patient ID.

    Returns
    -------
    List[dict]
        List of encounters with their admission dates.
        Format: [{"encounter_id": str, "admission_date": str}]
    """
    if ehr_data_manager.lazy_df is None:
        raise ValueError("Lazy DataFrame not initialized. Call init_lazy_df first.")

    try:
        # First get all events for the patient
        filtered_df = (
            ehr_data_manager.lazy_df.filter(pl.col("patient_id") == patient_id)
            .select(list(ehr_data_manager._required_columns))
            .collect(streaming=True)
        )

        if filtered_df.height == 0:
            logger.info(f"No events found for patient ID {patient_id}")
            return []

        # Process events to identify hospital admissions
        encounters = {}
        for row in filtered_df.to_dicts():
            processed_event = ehr_data_manager._process_event(row)
            # Check if this is a hospital admission event
            if processed_event["event_type"] == "HOSPITAL_ADMISSION":
                encounter_id = str(processed_event["encounter_id"])
                timestamp = processed_event["timestamp"]

                # Store only the earliest admission date for each encounter
                if (
                    encounter_id not in encounters
                    or timestamp < encounters[encounter_id]
                ):
                    encounters[encounter_id] = timestamp

        # Convert to list of dictionaries and sort by date
        encounter_list = [
            {
                "encounter_id": encounter_id,
                "admission_date": timestamp.strftime("%Y-%m-%d"),
            }
            for encounter_id, timestamp in encounters.items()
        ]

        # Sort by admission date
        encounter_list.sort(key=lambda x: x["admission_date"])

        return encounter_list

    except Exception:
        logger.error(
            f"Error fetching encounters for patient ID {patient_id}",
            exc_info=True,
        )
        raise


# Singleton instance
ehr_data_manager = EHRDataManager()


# Public interface functions
def init_lazy_df(directory: str) -> None:
    """Initialize the LazyFrame with the given directory."""
    ehr_data_manager.init_lazy_df(directory)


def fetch_recent_encounter_events(patient_id: int) -> List[Event]:
    """Fetch recent encounter events for a patient."""
    return ehr_data_manager.fetch_recent_encounter_events(patient_id)


def fetch_patient_events(patient_id: int) -> List[Event]:
    """Fetch all events for a patient."""
    return ehr_data_manager.fetch_patient_events(patient_id)


def fetch_patient_events_by_type(patient_id: int, event_type: str) -> List[Event]:
    """Fetch events filtered by event_type for a patient."""
    return ehr_data_manager.fetch_patient_events_by_type(patient_id, event_type)


def fetch_latest_medications(patient_id: int) -> str:
    """Fetch medication list from the latest encounter."""
    return ehr_data_manager.fetch_latest_medications(patient_id)
