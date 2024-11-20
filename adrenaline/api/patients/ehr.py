"""A module for loading EHR data from parquet files in MEDS format."""

import logging
import os
from typing import List, Optional

import polars as pl

from api.patients.data import Event


# Configure logging
logger = logging.getLogger(__name__)


class EHRDataManager:
    """A class to manage EHR data.

    Attributes
    ----------
    lazy_df : Optional[pl.LazyFrame]
        The lazy DataFrame containing the EHR data.
    """

    def __init__(self) -> None:
        """Initialize the EHRDataManager."""
        self.lazy_df: Optional[pl.LazyFrame] = None

    def init_lazy_df(self, directory: str) -> None:
        """Initialize the lazy DataFrame.

        Parameters
        ----------
        directory : str
            The directory containing the parquet files.
        """
        if self.lazy_df is None:
            parquet_files = [f for f in os.listdir(directory) if f.endswith(".parquet")]
            if not parquet_files:
                logger.error(f"No parquet files found in directory: {directory}")
                raise ValueError(f"No parquet files found in directory: {directory}")

            try:
                self.lazy_df = pl.scan_parquet(os.path.join(directory, "*.parquet"))
                # Verify that the required columns exist
                existing_columns = self.lazy_df.collect_schema().names()
                required_columns = [
                    "subject_id",
                    "hadm_id",
                    "code",
                    "description",
                    "time",
                    "numeric_value",
                    "text_value",
                ]
                missing_columns = set(required_columns) - set(existing_columns)
                if missing_columns:
                    raise ValueError(f"Missing required columns: {missing_columns}")

                # Rename columns to match Event dataclass
                self.lazy_df = self.lazy_df.rename(
                    {
                        "subject_id": "patient_id",
                        "hadm_id": "encounter_id",
                        "time": "timestamp",
                    }
                )
                logger.info("Lazy DataFrame initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing lazy DataFrame: {str(e)}")
                raise

    def fetch_patient_events(self, patient_id: int) -> List[Event]:
        """Fetch events for a patient.

        Parameters
        ----------
        patient_id : int
            The patient ID.

        Returns
        -------
        List[Event]
            The events for the patient.
        """
        if self.lazy_df is None:
            raise ValueError("Lazy DataFrame not initialized. Call init_lazy_df first.")

        try:
            filtered_df = (
                self.lazy_df.filter(pl.col("patient_id") == patient_id)
                .select(
                    [
                        "patient_id",
                        "encounter_id",
                        "code",
                        "description",
                        "timestamp",
                        "numeric_value",
                        "text_value",
                    ]
                )
                .collect()
            )

            return [
                Event(
                    patient_id=row["patient_id"],
                    encounter_id=row["encounter_id"],
                    code=row["code"],
                    description=row["description"],
                    timestamp=row["timestamp"],
                    numeric_value=row["numeric_value"],
                    text_value=row["text_value"],
                )
                for row in filtered_df.to_dicts()
            ]
        except Exception as e:
            logger.error(f"Error fetching events for patient ID {patient_id}: {str(e)}")
            raise

    def fetch_recent_encounter_events(self, patient_id: int) -> List[Event]:
        """Fetch events from the most recent encounter for a patient.

        Parameters
        ----------
        patient_id : int
            The patient ID.

        Returns
        -------
        List[Event]
            The events from the most recent encounter for the patient.
        """
        if self.lazy_df is None:
            raise ValueError("Lazy DataFrame not initialized. Call init_lazy_df first.")

        try:
            # First get the most recent encounter ID
            most_recent_encounter = (
                self.lazy_df
                .filter(pl.col("patient_id") == patient_id)
                .select([
                    "encounter_id",
                    "timestamp"
                ])
                .sort("timestamp", descending=True)
                .unique(subset="encounter_id")
                .limit(1)
                .collect()
            )

            if most_recent_encounter.height == 0:
                logger.warning(f"No encounters found for patient ID {patient_id}")
                return []

            recent_encounter_id = most_recent_encounter.get_column("encounter_id")[0]

            # Then fetch all events for this encounter
            filtered_df = (
                self.lazy_df
                .filter(
                    (pl.col("patient_id") == patient_id) & 
                    (pl.col("encounter_id") == recent_encounter_id)
                )
                .select([
                    "patient_id",
                    "encounter_id",
                    "code",
                    "description",
                    "timestamp",
                    "numeric_value",
                    "text_value"
                ])
                .sort("timestamp")
                .collect()
            )

            events = [
                Event(
                    patient_id=row["patient_id"],
                    encounter_id=row["encounter_id"],
                    code=row["code"],
                    description=row["description"],
                    timestamp=row["timestamp"],
                    numeric_value=row["numeric_value"],
                    text_value=row["text_value"],
                )
                for row in filtered_df.to_dicts()
            ]

            logger.info(
                f"Retrieved {len(events)} events from most recent encounter "
                f"{recent_encounter_id} for patient {patient_id}"
            )
            return events

        except Exception as e:
            logger.error(
                f"Error fetching recent encounter events for patient ID {patient_id}: {str(e)}"
            )
            raise


# Create a single instance of EHRDataManager
ehr_data_manager: EHRDataManager = EHRDataManager()


# Use these functions to interact with the EHRDataManager
def init_lazy_df(directory: str) -> None:
    """Initialize the lazy DataFrame.

    Parameters
    ----------
    directory : str
        The directory containing the parquet files.
    """
    ehr_data_manager.init_lazy_df(directory)


def fetch_recent_encounter_events(patient_id: int) -> List[Event]:
    """Fetch events from the most recent encounter for a patient.

    Parameters
    ----------
    patient_id : int
        The patient ID.

    Returns
    -------
    List[Event]
        The events from the most recent encounter for the patient.
    """
    return ehr_data_manager.fetch_recent_encounter_events(patient_id)


def fetch_patient_events(patient_id: int) -> List[Event]:
    """Fetch events for a patient.

    Parameters
    ----------
    patient_id : int
        The patient ID.

    Returns
    -------
    List[Event]
        The events for the patient.
    """
    return ehr_data_manager.fetch_patient_events(patient_id)


def fetch_patient_encounters(patient_id: int) -> List[int]:
    """Fetch encounters for a patient.

    Parameters
    ----------
    patient_id : int
        The patient ID.

    Returns
    -------
    List[int]
        The encounters for the patient.
    """
    if ehr_data_manager.lazy_df is None:
        raise ValueError("Lazy DataFrame not initialized. Call init_lazy_df first.")

    try:
        filtered_df = ehr_data_manager.lazy_df.filter(pl.col("patient_id") == patient_id)
        encounter_ids = (
            filtered_df
            .select("encounter_id")
            .unique()
            .collect()
            .get_column("encounter_id")
            .cast(pl.Utf8)
            .to_list()
        )
        encounter_ids = [str(eid) if eid is not None else "" for eid in encounter_ids]
        return encounter_ids
    except Exception as e:
        logger.error(f"Error fetching encounters for patient ID {patient_id}: {str(e)}")
        raise
