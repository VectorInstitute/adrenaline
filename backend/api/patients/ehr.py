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

    def __init__(self):
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
                existing_columns = self.lazy_df.columns
                required_columns = [
                    "subject_id",
                    "hadm_id",
                    "code",
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
                    timestamp=row["timestamp"],
                    numeric_value=row["numeric_value"],
                    text_value=row["text_value"],
                )
                for row in filtered_df.to_dicts()
            ]
        except Exception as e:
            logger.error(f"Error fetching events for patient ID {patient_id}: {str(e)}")
            raise


# Create a single instance of EHRDataManager
ehr_data_manager = EHRDataManager()


# Use these functions to interact with the EHRDataManager
def init_lazy_df(directory: str) -> None:
    """Initialize the lazy DataFrame.

    Parameters
    ----------
    directory : str
        The directory containing the parquet files.
    """
    ehr_data_manager.init_lazy_df(directory)


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
