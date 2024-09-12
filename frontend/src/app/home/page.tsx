'use client'

import React, { useState, useCallback } from 'react'
import {
  Box, Text, Flex, Heading, VStack, useColorModeValue, Button, Input,
  Container, Card, CardBody, SimpleGrid, Icon, useToast, InputGroup,
  InputLeftElement, Tabs, TabList, TabPanels, Tab, TabPanel, useBreakpointValue
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import { FaFileAlt, FaUser, FaSearch, FaQuestionCircle, FaCalendarAlt } from 'react-icons/fa'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import { PatientData } from '../types/patient'
import useSWR from 'swr'
import StatCard from '../components/stat-card'
import ClinicalNotesCard from '../components/clinical-notes-card'
import ClinicalNotesTable from '../components/clinical-notes-table'
import QAPairsTable from '../components/qapairs-table'
import EventsTable from '../components/events-table'

interface DatabaseSummary {
  total_patients: number;
  total_notes: number;
  total_qa_pairs: number;
  total_events: number;
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

  const containerMaxWidth = useBreakpointValue({ base: 'container.sm', md: 'container.md', lg: 'container.xl' })

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
    <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6}>
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
      <StatCard
        icon={FaCalendarAlt}
        title="Events"
        value={patientData ? patientData.events?.length ?? 0 : dbSummary?.total_events ?? 0}
        color="orange"
        isLoading={!dbSummary && !dbSummaryError}
      />
    </SimpleGrid>
  )

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s" p={6}>
        <Container maxW={containerMaxWidth}>
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
                    <TabList mb={4} flexWrap="wrap">
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }}>Clinical Notes</Tab>
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }}>QA Pairs</Tab>
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }}>Events</Tab>
                    </TabList>

                    <TabPanels>
                      <TabPanel px={0}>
                        <ClinicalNotesTable notes={patientData.notes} handleNoteClick={handleNoteClick} />
                      </TabPanel>
                      <TabPanel px={0}>
                        <QAPairsTable qaPairs={patientData.qa_data} />
                      </TabPanel>
                      <TabPanel px={0}>
                        <EventsTable events={patientData.events} />
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

export default withAuth(HomePage)
