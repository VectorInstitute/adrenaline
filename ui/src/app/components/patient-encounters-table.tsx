import React from 'react'
import {
  Card,
  CardBody,
  Heading,
  TableContainer,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Skeleton,
  Text,
  useColorModeValue
} from '@chakra-ui/react'

interface Encounter {
  encounter_id: string;
  admission_date: string;
}

interface PatientEncountersTableProps {
  encounters: Encounter[];
  isLoading: boolean;
}

const PatientEncountersTable: React.FC<PatientEncountersTableProps> = ({
  encounters,
  isLoading
}) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.600')
  const headerBgColor = useColorModeValue('gray.50', 'gray.700')

  return (
    <Card
      bg={cardBgColor}
      shadow="md"
      mt={6}
      borderWidth={1}
      borderColor={borderColor}
    >
      <CardBody>
        <Heading
          as="h3"
          size="md"
          mb={4}
          color="#1f5280"
          fontFamily="'Roboto Slab', serif"
        >
          Patient Encounters
        </Heading>
        {isLoading ? (
          <Skeleton height="200px" />
        ) : encounters.length > 0 ? (
          <TableContainer>
            <Table variant="simple" size="sm">
              <Thead>
                <Tr bg={headerBgColor}>
                  <Th>Encounter ID</Th>
                  <Th>Admission Date</Th>
                </Tr>
              </Thead>
              <Tbody>
                {encounters.map((encounter, index) => (
                  <Tr
                    key={index}
                    _hover={{ bg: headerBgColor }}
                    transition="background-color 0.2s"
                  >
                    <Td>{encounter.encounter_id}</Td>
                    <Td>{new Date(encounter.admission_date).toLocaleDateString()}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TableContainer>
        ) : (
          <Text>No encounters found</Text>
        )}
      </CardBody>
    </Card>
  )
}

export default PatientEncountersTable
