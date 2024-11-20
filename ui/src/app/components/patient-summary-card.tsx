import React from 'react'
import {
  Card,
  CardBody,
  Heading,
  Text,
  VStack,
  HStack,
  Icon,
  useColorModeValue,
  Divider
} from '@chakra-ui/react'
import {
  FaUserAlt,
  FaCalendarAlt,
  FaVenusMars,
  FaClipboardList,
  FaNotesMedical
} from 'react-icons/fa'
import { PatientData } from '../types/patient'

interface PatientSummaryCardProps {
  patientData: PatientData
}

const SummaryItem: React.FC<{
  icon: React.ElementType;
  label: string;
  value: string | number;
}> = ({ icon, label, value }) => (
  <HStack spacing={3} width="100%">
    <Icon as={icon} color="#1f5280" boxSize={4} />
    <Text fontWeight="bold" minWidth="80px">{label}:</Text>
    <Text>{value}</Text>
  </HStack>
)

const PatientSummaryCard: React.FC<PatientSummaryCardProps> = ({ patientData }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.600')

  return (
    <Card
      bg={cardBgColor}
      shadow="md"
      borderWidth={1}
      borderColor={borderColor}
      transition="transform 0.2s"
      _hover={{ transform: 'translateY(-2px)' }}
    >
      <CardBody>
        <VStack spacing={4} align="stretch">
          <Heading
            as="h2"
            size="md"
            color="#1f5280"
            fontFamily="'Roboto Slab', serif"
          >
            Patient Summary
          </Heading>
          <Divider />
          <SummaryItem
            icon={FaUserAlt}
            label="ID"
            value={patientData.patient_id}
          />
          <SummaryItem
            icon={FaCalendarAlt}
            label="Age"
            value={patientData.age}
          />
          <SummaryItem
            icon={FaVenusMars}
            label="Gender"
            value={patientData.gender}
          />
          <SummaryItem
            icon={FaClipboardList}
            label="Events"
            value={patientData.events?.length || 0}
          />
          <SummaryItem
            icon={FaNotesMedical}
            label="Notes"
            value={patientData.notes?.length || 0}
          />
        </VStack>
      </CardBody>
    </Card>
  )
}

export default PatientSummaryCard
