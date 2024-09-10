'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Text, Flex, Heading, VStack, useColorModeValue, Button, Input,
  Container, Card, CardBody, SimpleGrid, Icon, Table, Thead, Tbody, Tr,
  Th, Td, useToast, Skeleton, InputGroup, InputLeftElement, Divider, Tag,
  Tooltip, Badge, IconButton, Tabs, TabList, TabPanels, Tab, TabPanel
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import { FaFileAlt, FaUser, FaHospital, FaSearch, FaEye, FaDatabase, FaQuestionCircle } from 'react-icons/fa'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import { PatientData, ClinicalNote, QAPair } from '../types/patient'

const HomePage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('')
  const [patientData, setPatientData] = useState<PatientData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [dbSummary, setDbSummary] = useState<{ total_patients: number; total_notes: number; total_qa_pairs: number } | null>(null)
  const [isLoadingDbSummary, setIsLoadingDbSummary] = useState<boolean>(true)

  const router = useRouter()
  const toast = useToast()

  const primaryColor = useColorModeValue('teal.500', 'teal.300')
  const secondaryColor = useColorModeValue('blue.500', 'blue.300')
  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const borderColor = useColorModeValue('gray.200', 'gray.700')

  const fetchDatabaseSummary = useCallback(async () => {
    setIsLoadingDbSummary(true);
    try {
      const response = await fetch('/api/database_summary', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch database summary');
      }
      const data = await response.json();
      console.log('Database summary data:', data);
      setDbSummary({
        total_patients: data.total_patients || 0,
        total_notes: data.total_notes || 0,
        total_qa_pairs: data.total_qa_pairs || 0,
      });
    } catch (error) {
      console.error('Error fetching database summary:', error);
      toast({
        title: "Error",
        description: "Failed to fetch database summary",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      // Set default values in case of error
      setDbSummary({
        total_patients: 0,
        total_notes: 0,
        total_qa_pairs: 0,
      });
    } finally {
      setIsLoadingDbSummary(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchDatabaseSummary()
  }, [fetchDatabaseSummary])

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

      const data = await response.json()
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

            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
              <StatCard
                icon={FaDatabase}
                title="Total Patients"
                value={dbSummary?.total_patients ?? 0}
                color="teal"
                isLoading={isLoadingDbSummary}
              />
              <StatCard
                icon={FaFileAlt}
                title="Total Notes"
                value={dbSummary?.total_notes ?? 0}
                color="blue"
                isLoading={isLoadingDbSummary}
              />
              <StatCard
                icon={FaQuestionCircle}
                title="Total QA Pairs"
                value={dbSummary?.total_qa_pairs ?? 0}
                color="purple"
                isLoading={isLoadingDbSummary}
              />
            </SimpleGrid>

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
                  <Tabs>
                    <TabList>
                      <Tab>Clinical Notes</Tab>
                      <Tab>QA Pairs</Tab>
                    </TabList>

                    <TabPanels>
                      <TabPanel>
                        <ClinicalNotesTable notes={patientData.notes} handleNoteClick={handleNoteClick} />
                      </TabPanel>
                      <TabPanel>
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
  const cardBgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

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
              {value !== undefined ? value : 'N/A'}
            </Text>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

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
