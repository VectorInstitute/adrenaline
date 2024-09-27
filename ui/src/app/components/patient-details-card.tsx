import React from 'react'
import {
  Card, CardBody, Tabs, TabList, TabPanels, Tab, TabPanel, useColorModeValue, Box
} from '@chakra-ui/react'
import { PatientData } from '../types/patient'
import EventsTable from './events-table'
import ClinicalNotesTable from './clinical-notes-table'
import QAPairsTable from './qapairs-table'

interface PatientDetailsCardProps {
  patientData: PatientData;
  patientId: string;
}

const PatientDetailsCard: React.FC<PatientDetailsCardProps> = ({ patientData, patientId }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.600')
  const tabBg = useColorModeValue('gray.100', 'gray.700')
  const activeTabBg = useColorModeValue('white', 'gray.600')

  return (
    <Card bg={cardBgColor} shadow="md" borderWidth={1} borderColor={borderColor}>
      <CardBody>
        <Tabs variant="enclosed" colorScheme="blue">
          <TabList mb={4}>
            <Tab _selected={{ bg: activeTabBg }} bg={tabBg}>Events</Tab>
            <Tab _selected={{ bg: activeTabBg }} bg={tabBg}>Clinical Notes</Tab>
            <Tab _selected={{ bg: activeTabBg }} bg={tabBg}>QA Pairs</Tab>
          </TabList>
          <TabPanels>
            <TabPanel px={0}>
              <Box maxHeight="60vh" overflowY="auto">
                <EventsTable events={patientData.events} />
              </Box>
            </TabPanel>
            <TabPanel px={0}>
              <Box maxHeight="60vh" overflowY="auto">
                <ClinicalNotesTable notes={patientData.notes} patientId={patientId} />
              </Box>
            </TabPanel>
            <TabPanel px={0}>
              <Box maxHeight="60vh" overflowY="auto">
                <QAPairsTable qaPairs={patientData.qa_data} />
              </Box>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </CardBody>
    </Card>
  )
}

export default PatientDetailsCard
