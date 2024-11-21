"""Script to load MIMIC-IV data into a FHIR server."""

import gzip
import json
import requests
from pathlib import Path
import logging
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("MIMIC FHIR Loader")

# Define MIMIC-IV FHIR resource loading order based on dependencies
RESOURCE_LOAD_ORDER = [
    # Base resources with no dependencies
    "MimicOrganization",  # Healthcare organization info
    "MimicLocation",  # Hospital locations
    "MimicPatient",  # Patient demographics
    # Encounter resources
    "MimicEncounter",  # Hospital admissions
    "MimicEncounterED",  # Emergency department visits
    "MimicEncounterICU",  # ICU stays
    # Medication-related resources
    "MimicMedication",  # Medication catalog
    "MimicMedicationMix",  # Medication mixtures
    "MimicMedicationRequest",  # Medication orders
    "MimicMedicationDispense",  # Medication dispensing
    "MimicMedicationDispenseED",  # ED medication dispensing
    "MimicMedicationAdministration",  # Medication administration
    "MimicMedicationAdministrationICU",  # ICU medication administration
    "MimicMedicationStatementED",  # ED medication statements
    # Clinical resources
    "MimicSpecimen",  # Specimen collection
    "MimicSpecimenLab",  # Laboratory specimens
    "MimicCondition",  # Diagnoses and conditions
    "MimicConditionED",  # ED diagnoses
    "MimicProcedure",  # Hospital procedures
    "MimicProcedureED",  # ED procedures
    "MimicProcedureICU",  # ICU procedures
    # Observation resources (largest files last)
    "MimicObservationED",  # ED observations
    "MimicObservationVitalSignsED",  # ED vital signs
    "MimicObservationMicroOrg",  # Microbiology organisms
    "MimicObservationMicroTest",  # Microbiology tests
    "MimicObservationMicroSusc",  # Microbiology susceptibilities
    "MimicObservationDatetimeevents",  # Datetime events
    "MimicObservationOutputevents",  # Output events
    "MimicObservationLabevents",  # Laboratory results
    "MimicObservationChartevents",  # Charted events
]


def send_to_fhir(bundle, fhir_base_url):
    """Send bundle to FHIR server."""
    headers = {"Content-Type": "application/fhir+json"}
    try:
        response = requests.post(fhir_base_url, json=bundle, headers=headers)
        if response.status_code not in [200, 201]:
            logger.error(f"Error response: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"Failed to send bundle to FHIR server: {e}")
        return None


def create_transaction_bundle(resources):
    """Create a FHIR transaction bundle from a list of resources."""
    entries = []
    for res in resources:
        # Ensure the resource has an id
        if "id" not in res:
            logger.warning(f"Resource missing id: {res.get('resourceType', 'Unknown')}")
            continue

        entries.append(
            {
                "resource": res,
                "request": {
                    "method": "PUT",  # Use PUT instead of POST to ensure id is preserved
                    "url": f"{res['resourceType']}/{res['id']}",
                },
            }
        )

    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def load_ndjson_to_fhir(file_path, fhir_base_url, batch_size=50):  # Smaller batch size
    """Load NDJSON file into FHIR server."""
    logger.info(f"Loading data from {file_path}...")
    file_size = file_path.stat().st_size / (1024 * 1024)  # Size in MB
    logger.info(f"File size: {file_size:.1f} MB")

    with gzip.open(file_path, "rt") as f:
        batch = []
        total_loaded = 0
        failed_batches = 0

        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Loading {file_path.name}", total=None)

            for line_number, line in enumerate(f, 1):
                try:
                    resource = json.loads(line)

                    # Ensure resource has an id
                    if "id" not in resource:
                        resource["id"] = f"{line_number}"

                    batch.append(resource)

                    if len(batch) >= batch_size:
                        bundle = create_transaction_bundle(batch)
                        response = send_to_fhir(bundle, fhir_base_url)

                        if response and response.status_code in [200, 201]:
                            total_loaded += len(batch)
                            progress.update(task, advance=len(batch))
                        else:
                            failed_batches += 1
                            logger.error(f"Failed to load batch at line {line_number}")
                        batch = []

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON at line {line_number}: {line[:100]}...")
                except Exception as e:
                    logger.error(f"Error processing line {line_number}: {str(e)}")

            # Process remaining resources
            if batch:
                bundle = create_transaction_bundle(batch)
                response = send_to_fhir(bundle, fhir_base_url)

                if response and response.status_code in [200, 201]:
                    total_loaded += len(batch)
                    progress.update(task, advance=len(batch))
                else:
                    failed_batches += 1
                    logger.error("Failed to load final batch")

    logger.info(
        f"✅ Completed loading {total_loaded} resources from {file_path.name}"
        f" ({failed_batches} failed batches)"
    )
    return total_loaded, failed_batches


def main():
    port = "8087"  # Change this to match your FHIR server port
    fhir_base_url = f"http://localhost:{port}/fhir"
    data_dir = Path("/Volumes/clinical-data/physionet.org/files/mimic-iv-fhir/1.0/fhir")

    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return

    # Test server connection
    try:
        response = requests.get(f"{fhir_base_url}/metadata")
        response.raise_for_status()
        logger.info("Successfully connected to FHIR server")
    except requests.RequestException as e:
        logger.error(f"Failed to connect to FHIR server: {e}")
        return

    # Process files in the specified order
    total_resources = 0
    total_failed = 0

    for resource_type in RESOURCE_LOAD_ORDER:
        resource_file = data_dir / f"{resource_type}.ndjson.gz"
        if resource_file.exists():
            logger.info(f"\n=== Loading {resource_type} resources ===")
            loaded, failed = load_ndjson_to_fhir(resource_file, fhir_base_url)
            total_resources += loaded
            total_failed += failed
        else:
            logger.warning(f"File not found: {resource_file}")

    logger.info("\n=== Loading Complete ===")
    logger.info(f"Total resources loaded: {total_resources}")
    logger.info(f"Total failed batches: {total_failed}")


if __name__ == "__main__":
    main()
