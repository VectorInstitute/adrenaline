export interface MedicalNote {
    note_id: string;
    patient_id: number;
    encounter_id: string;
    text: string;
    timestamp: Date;
  }
