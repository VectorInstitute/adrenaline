import React from 'react'
import {
  Card, CardBody, Heading, Text, VStack, HStack, Icon, useColorModeValue
} from '@chakra-ui/react'
import { FaUserAlt, FaCalendarAlt, FaVenusMars } from 'react-icons/fa'
import { PatientData } from '../types/patient'

interface PatientSummaryCardProps {
  patientData: PatientData
}

const PatientSummaryCard: React.FC<PatientSummaryCardProps> = ({ patientData }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.600')

  return (
    <Card bg={cardBgColor} shadow="md" borderWidth={1} borderColor={borderColor}>
      <CardBody>
        <VStack spacing={4} align="stretch">
          <Heading as="h2" size="md" color="#1f5280">Patient Summary</Heading>
          <HStack>
            <Icon as={FaUserAlt} color="#1f5280" />
            <Text fontWeight="bold">ID:</Text>
            <Text>{patientData.patient_id}</Text>
          </HStack>
          <HStack>
            <Icon as={FaCalendarAlt} color="#1f5280" />
            <Text fontWeight="bold">Age:</Text>
            <Text>{patientData.age}</Text>
          </HStack>
          <HStack>
            <Icon as={FaVenusMars} color="#1f5280" />
            <Text fontWeight="bold">Gender:</Text>
            <Text>{patientData.gender}</Text>
          </HStack>
          <HStack>
            <Text fontWeight="bold">Events:</Text>
            <Text>{patientData.events?.length || 0}</Text>
          </HStack>
          <HStack>
            <Text fontWeight="bold">Notes:</Text>
            <Text>{patientData.notes?.length || 0}</Text>
          </HStack>
        </VStack>
      </CardBody>
    </Card>
  )
}

export default PatientSummaryCard
