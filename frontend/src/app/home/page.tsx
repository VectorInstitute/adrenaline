'use client'

import React, { useState, useCallback } from 'react'
import {
  Box, Text, Flex, Heading, VStack, useColorModeValue, Button, Input,
  Container, Card, CardBody, SimpleGrid, Icon, Table, Thead, Tbody, Tr,
  Th, Td, useToast, Skeleton, InputGroup, InputLeftElement, Tabs, TabList,
  TabPanels, Tab, TabPanel, Tag, Badge, Tooltip, IconButton, Divider,
  HStack, Wrap, WrapItem, Center
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import { FaFileAlt, FaUser, FaSearch, FaQuestionCircle, FaEye } from 'react-icons/fa'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import { PatientData, ClinicalNote, QAPair } from '../types/patient'
import useSWR from 'swr'

interface DatabaseSummary {
  total_patients: number;
  total_notes: number;
  total_qa_pairs: number;
}

const fetcher = (url: string) => fetch(url, {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`,
  },
}).then(res => res.json())

const HomePage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('')
  const [patientData, setPatientData] = useState<PatientData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)

  const { data: dbSummary, error: dbSummaryError } = useSWR<DatabaseSummary>('/api/database_summary', fetcher, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    refreshInterval: 300000,
  })

  const router = useRouter()
  const toast = useToast()

  const primaryColor = useColorModeValue('teal.500', 'teal.300')
  const secondaryColor = useColorModeValue('blue.500', 'blue.300')
  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const borderColor = useColorModeValue('gray.200', 'gray.700')

  const loadPatientData = useCallback(async () => {
    if (!patientId.trim()) {
      toast({
        title: "Error",
        description: "Please enter a patient ID",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return
    }

    if (isNaN(Number(patientId))) {
      toast({
        title: "Error",
        description: "Patient ID must be a number",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`/api/patient_data/${patientId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (response.status === 404) {
        setPatientData(null)
        toast({
          title: "Info",
          description: "No data found for this patient",
          status: "info",
          duration: 3000,
          isClosable: true,
        })
        return
      }

      if (!response.ok) {
        throw new Error('Failed to fetch patient data')
      }

      const data: PatientData = await response.json()
      setPatientData(data)
      toast({
        title: "Success",
        description: "Patient data loaded successfully",
        status: "success",
        duration: 3000,
        isClosable: true,
      })
    } catch (error) {
      console.error('Error loading patient data:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while loading patient data",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      setPatientData(null)
    } finally {
      setIsLoading(false)
    }
  }, [patientId, toast])

  const handleNoteClick = useCallback((noteId: string) => {
    router.push(`/note/${patientId}/${noteId}`)
  }, [patientId, router])

  const renderSummary = () => (
    <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
      <StatCard
        icon={FaUser}
        title="Total Patients"
        value={patientData ? 1 : dbSummary?.total_patients ?? 0}
        color="teal"
        isLoading={!dbSummary && !dbSummaryError}
      />
      <ClinicalNotesCard
        patientData={patientData}
        dbTotalNotes={dbSummary?.total_notes ?? 0}
        isLoading={!dbSummary && !dbSummaryError}
      />
      <StatCard
        icon={FaQuestionCircle}
        title="QA Pairs"
        value={patientData ? patientData.qa_data?.length ?? 0 : dbSummary?.total_qa_pairs ?? 0}
        color="purple"
        isLoading={!dbSummary && !dbSummaryError}
      />
    </SimpleGrid>
  )

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s" p={6}>
        <Container maxW="container.xl">
          <VStack spacing={8} align="stretch">
            <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h1" size="xl" color={primaryColor} mb={4}>Clinical Data Dashboard</Heading>
                <Text fontSize="lg" color={textColor}>View and analyze patient clinical data.</Text>
              </CardBody>
            </Card>

            {renderSummary()}

            <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h2" size="lg" color={secondaryColor} mb={6}>Load Patient Data</Heading>
                <Flex direction={{ base: 'column', md: 'row' }} mb={4} align="center" gap={4}>
                  <InputGroup flex={1}>
                    <InputLeftElement pointerEvents="none">
                      <Icon as={FaSearch} color="gray.300" />
                    </InputLeftElement>
                    <Input
                      value={patientId}
                      onChange={(e) => setPatientId(e.target.value)}
                      placeholder="Enter Patient ID..."
                      bg={cardBgColor}
                      borderColor={borderColor}
                      _hover={{ borderColor: primaryColor }}
                    />
                  </InputGroup>
                  <Button
                    colorScheme="teal"
                    onClick={loadPatientData}
                    isLoading={isLoading}
                    loadingText="Loading..."
                    size="lg"
                    width={{ base: 'full', md: 'auto' }}
                  >
                    Load Patient Data
                  </Button>
                </Flex>
              </CardBody>
            </Card>

            {patientData && (
              <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
                <CardBody>
                  <Heading as="h2" size="lg" color={secondaryColor} mb={6}>Patient Data</Heading>
                  <Tabs variant="soft-rounded" colorScheme="teal">
                    <TabList mb={4}>
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }}>Clinical Notes</Tab>
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }}>QA Pairs</Tab>
                    </TabList>

                    <TabPanels>
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
            )}
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

interface StatCardProps {
  icon: React.ElementType;
  title: string;
  value: string | number;
  color: string;
  isLoading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ icon, title, value, color, isLoading = false }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')

  return (
    <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="md" borderWidth={1} borderColor={borderColor}>
      <CardBody>
        <VStack spacing={4} align="center">
          <Icon as={icon} boxSize={10} color={`${color}.500`} />
          <Heading size="md" textAlign="center">{title}</Heading>
          {isLoading ? (
            <Skeleton height="24px" width="60px" />
          ) : (
            <Text fontSize="2xl" fontWeight="bold" color={`${color}.500`}>
              {value}
            </Text>
          )}
        </VStack>
      </CardBody>
    </Card>
  )
}

interface ClinicalNotesCardProps {
  patientData: PatientData | null;
  dbTotalNotes: number;
  isLoading: boolean;
}

const ClinicalNotesCard: React.FC<ClinicalNotesCardProps> = ({ patientData, dbTotalNotes, isLoading }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')

  const renderContent = () => {
    if (isLoading) {
      return <Skeleton height="24px" width="60px" />
    }

    if (patientData) {
      const noteCounts = patientData.notes.reduce((acc, note) => {
        acc[note.note_type] = (acc[note.note_type] || 0) + 1
        return acc
      }, {} as Record<string, number>)

      return (
        <VStack align="center" spacing={2} width="100%">
          <Text fontSize="2xl" fontWeight="bold" color="blue.500">
            {patientData.notes.length}
          </Text>
          <Wrap justify="center" spacing={2}>
            {Object.entries(noteCounts).map(([type, count]) => (
              <WrapItem key={type}>
                <Badge colorScheme="blue" fontSize="sm" px={2} py={1} borderRadius="full">
                  {type}: {count}
                </Badge>
              </WrapItem>
            ))}
          </Wrap>
        </VStack>
      )
    }

    return (
      <Text fontSize="2xl" fontWeight="bold" color="blue.500">
        {dbTotalNotes}
      </Text>
    )
  }

  return (
    <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="md" borderWidth={1} borderColor={borderColor}>
      <CardBody>
        <VStack spacing={4} align="center">
          <Icon as={FaFileAlt} boxSize={10} color="blue.500" />
          <Heading size="md" textAlign="center">Clinical Notes</Heading>
          <Center width="100%">
            {renderContent()}
          </Center>
        </VStack>
      </CardBody>
    </Card>
  )
}

interface ClinicalNotesTableProps {
  notes: ClinicalNote[];
  handleNoteClick: (noteId: string) => void;
}

const ClinicalNotesTable: React.FC<ClinicalNotesTableProps> = ({ notes, handleNoteClick }) => {
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const tableBorderColor = useColorModeValue('gray.200', 'gray.600')
  const tableHoverBg = useColorModeValue('gray.100', 'gray.700')
  const tableHeaderBg = useColorModeValue('gray.100', 'gray.700')

  return (
    <Box overflowX="auto">
      <Table variant="simple" size="sm">
        <Thead>
          <Tr bg={tableHeaderBg}>
            <Th borderColor={tableBorderColor}>Note ID</Th>
            <Th borderColor={tableBorderColor}>Encounter ID</Th>
            <Th borderColor={tableBorderColor}>Timestamp</Th>
            <Th borderColor={tableBorderColor}>Note Type</Th>
            <Th borderColor={tableBorderColor}>Text Preview</Th>
            <Th borderColor={tableBorderColor}>Action</Th>
          </Tr>
        </Thead>
        <Tbody>
          {notes.map((note, index) => (
            <React.Fragment key={note.note_id}>
              <Tr _hover={{ bg: tableHoverBg }} transition="background-color 0.2s" cursor="pointer" onClick={() => handleNoteClick(note.note_id)}>
                <Td borderColor={tableBorderColor}>
                  <Tag colorScheme="blue" variant="solid">{note.note_id}</Tag>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <Badge colorScheme="purple">
                    {note.encounter_id === '-1' ? 'N/A' : note.encounter_id}
                  </Badge>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <Text fontSize="sm" color={textColor}>{new Date(note.timestamp).toLocaleString()}</Text>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <Badge colorScheme="green">{note.note_type}</Badge>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <Tooltip label={note.text} placement="top" hasArrow>
                    <Text fontSize="sm" color={textColor} isTruncated maxWidth="200px">
                      {note.text.substring(0, 50)}...
                    </Text>
                  </Tooltip>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <IconButton
                    aria-label="View note"
                    icon={<FaEye />}
                    size="sm"
                    colorScheme="blue"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleNoteClick(note.note_id);
                    }}
                  />
                </Td>
              </Tr>
              {index < notes.length - 1 && (
                <Tr>
                  <Td colSpan={6} p={0}>
                    <Divider borderColor={tableBorderColor} />
                  </Td>
                </Tr>
              )}
            </React.Fragment>
          ))}
        </Tbody>
      </Table>
    </Box>
  )
}

interface QAPairsTableProps {
  qaPairs: QAPair[];
}

const QAPairsTable: React.FC<QAPairsTableProps> = ({ qaPairs }) => {
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const tableBorderColor = useColorModeValue('gray.200', 'gray.600')
  const tableHoverBg = useColorModeValue('gray.100', 'gray.700')
  const tableHeaderBg = useColorModeValue('gray.100', 'gray.700')

  return (
    <Box overflowX="auto">
      <Table variant="simple" size="sm">
        <Thead>
          <Tr bg={tableHeaderBg}>
            <Th borderColor={tableBorderColor}>Question</Th>
            <Th borderColor={tableBorderColor}>Answer</Th>
          </Tr>
        </Thead>
        <Tbody>
          {qaPairs.map((qaPair, index) => (
            <React.Fragment key={index}>
              <Tr _hover={{ bg: tableHoverBg }} transition="background-color 0.2s">
                <Td borderColor={tableBorderColor}>
                  <Text fontSize="sm" color={textColor}>{qaPair.question}</Text>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <Text fontSize="sm" color={textColor}>{qaPair.answer}</Text>
                </Td>
              </Tr>
              {index < qaPairs.length - 1 && (
                <Tr>
                  <Td colSpan={2} p={0}>
                    <Divider borderColor={tableBorderColor} />
                  </Td>
                </Tr>
              )}
            </React.Fragment>
          ))}
        </Tbody>
      </Table>
    </Box>
  )
}

export default withAuth(HomePage)
