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
  useColorModeValue,
  Box
} from '@chakra-ui/react'
import { Encounter, PatientEncountersTableProps } from '../types/patient'


const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date)
}

const PatientEncountersTable: React.FC<PatientEncountersTableProps> = ({
  encounters,
  isLoading
}) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.600')
  const headerBgColor = useColorModeValue('blue.50', 'blue.900')
  const rowHoverBg = useColorModeValue('gray.50', 'gray.700')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const headerTextColor = useColorModeValue('blue.700', 'blue.100')

  return (
    <Card
      bg={cardBgColor}
      shadow="lg"
      mt={6}
      borderWidth={1}
      borderColor={borderColor}
      borderRadius="xl"
      overflow="hidden"
    >
      <CardBody p={0}>
        <Box p={6} borderBottom="1px" borderColor={borderColor}>
          <Heading
            as="h3"
            size="md"
            color="#1f5280"
            fontFamily="'Roboto Slab', serif"
          >
            Patient Encounters
          </Heading>
        </Box>

        {isLoading ? (
          <Box p={6}>
            <Skeleton height="200px" />
          </Box>
        ) : encounters.length > 0 ? (
          <TableContainer>
            <Table variant="simple" size="md">
              <Thead>
                <Tr>
                  <Th
                    bg={headerBgColor}
                    py={4}
                    color={headerTextColor}
                    fontSize="sm"
                    borderBottom="2px"
                    borderColor="blue.500"
                  >
                    Encounter ID
                  </Th>
                  <Th
                    bg={headerBgColor}
                    py={4}
                    color={headerTextColor}
                    fontSize="sm"
                    borderBottom="2px"
                    borderColor="blue.500"
                  >
                    Admission Date
                  </Th>
                </Tr>
              </Thead>
              <Tbody>
                {encounters.map((encounter, index) => (
                  <Tr
                    key={index}
                    _hover={{ bg: rowHoverBg }}
                    transition="background-color 0.2s"
                  >
                    <Td
                      py={2}
                      color={textColor}
                      borderBottom="1px"
                      borderColor={borderColor}
                      fontWeight="medium"
                    >
                      {encounter.encounter_id}
                    </Td>
                    <Td
                      py={2}
                      color={textColor}
                      borderBottom="1px"
                      borderColor={borderColor}
                    >
                      {formatDate(encounter.admission_date)}
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TableContainer>
        ) : (
          <Box p={6}>
            <Text
              color={textColor}
              fontSize="md"
              textAlign="center"
              fontStyle="italic"
            >
              No encounters found
            </Text>
          </Box>
        )}
      </CardBody>
    </Card>
  )
}

export default PatientEncountersTable
