import React from 'react'
import {
  Card,
  CardBody,
  Heading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react'
import { PatientData } from '../types/patient'
import ClinicalNotesTable from './clinical-notes-table'
import QAPairsTable from './qapairs-table'
import EventsTable from './events-table'

interface PatientCardProps {
  patientData: PatientData
  handleNoteClick: (noteId: string) => void
}

const PatientCard: React.FC<PatientCardProps> = ({ patientData, handleNoteClick }) => {
  return (
    <Card p={4} borderRadius="xl" shadow="lg" borderWidth={1} borderColor="teal.200" width="100%">
      <CardBody>
        <Heading as="h2" size="md" mb={4} color="teal.600">
          Patient ID: {patientData.patient_id}
        </Heading>
        <Tabs variant="soft-rounded" colorScheme="blue" size="sm">
          <TabList mb={4} flexWrap="wrap" gap={2}>
            <Tab _selected={{ color: 'white', bg: 'blue.500' }} fontWeight="medium">Events</Tab>
            <Tab _selected={{ color: 'white', bg: 'blue.500' }} fontWeight="medium">Clinical Notes</Tab>
            <Tab _selected={{ color: 'white', bg: 'blue.500' }} fontWeight="medium">QA Pairs</Tab>
          </TabList>
          <TabPanels>
            <TabPanel px={0}>
              <EventsTable events={patientData.events} />
            </TabPanel>
            <TabPanel px={0}>
              <ClinicalNotesTable notes={patientData.notes} handleNoteClick={handleNoteClick} />
            </TabPanel>
            <TabPanel px={0}>
              <QAPairsTable qaPairs={patientData.qa_data} />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </CardBody>
    </Card>
  )
}

export default PatientCard
