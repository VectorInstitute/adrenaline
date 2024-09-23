
import React from 'react'
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
} from '@chakra-ui/react'
import { PatientData } from '../types/patient'

interface PatientTableProps {
  patients: PatientData[]
}

const PatientTable: React.FC<PatientTableProps> = ({ patients }) => {
  return (
    <TableContainer>
      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Patient ID</Th>
            <Th>Notes Count</Th>
            <Th>Events Count</Th>
          </Tr>
        </Thead>
        <Tbody>
          {patients.map((patient) => (
            <Tr key={patient.patient_id}>
              <Td>{patient.patient_id}</Td>
              <Td>{patient.notes.length}</Td>
              <Td>{patient.events.length}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </TableContainer>
  )
}

export default PatientTable
