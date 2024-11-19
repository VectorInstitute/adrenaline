export interface ClinicalNote {
    note_id: string;
    encounter_id: string;
    timestamp: string;
    text: string;
    note_type: string;
  }

  export interface QAPair {
    question: string;
    answer: string;
  }

  export interface PatientData {
    patient_id: number;
    notes: ClinicalNote[];
    qa_data: QAPair[];
    events: Event[];
  }

  export interface Event {
    patient_id: number;
    encounter_id: string;
    code: string;
    description: string;
    timestamp: string;
    numeric_value: number;
    text_value: string;
  }

  export interface MetaAnnotation {
    value: string;
    confidence: number;
    name: string;
  }

  export interface Entity {
    pretty_name: string;
    cui: string;
    type_ids: string[];
    types: string[];
    source_value: string;
    detected_name: string;
    acc: number;
    context_similarity: number;
    start: number;
    end: number;
    icd10: Array<{ chapter: string; name: string }>;
    ontologies: string[];
    snomed: string[];
    id: number;
    meta_anns: Record<string, MetaAnnotation>;
  }

  export interface NERResponse {
    note_id: string;
    text: string;
    entities: Entity[];
  }
