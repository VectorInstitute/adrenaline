'use client'

import React, { useState, useCallback, useMemo } from 'react'
import {
  Box, Text, Flex, Heading, VStack, useColorModeValue, Button, Input,
  Container, Card, CardBody, SimpleGrid, Icon, useToast, InputGroup,
  InputLeftElement, Tabs, TabList, TabPanels, Tab, TabPanel, useBreakpointValue,
  Divider, Stack
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
  total_events: 'N/A';
}

const fetcher = async (url: string): Promise<DatabaseSummary> => {
  const token = localStorage.getItem('token')
  if (!token) throw new Error('No token found')

  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
  if (!res.ok) throw new Error('Failed to fetch data')
  return res.json()
}

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

  const primaryColor = useColorModeValue('teal.600', 'teal.300')
  const secondaryColor = useColorModeValue('blue.600', 'blue.300')
  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const borderColor = useColorModeValue('gray.200', 'gray.700')
  const headingColor = useColorModeValue('gray.700', 'gray.200')

  const containerMaxWidth = useBreakpointValue({ base: '100%', sm: 'container.sm', md: 'container.md', lg: 'container.xl' })

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

    const patientIdNumber = Number(patientId)
    if (isNaN(patientIdNumber)) {
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
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch(`/api/patient_data/${patientIdNumber}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
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

  const handlePatientIdChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setPatientId(e.target.value)
  }, [])

  const renderSummary = useMemo(() => (
    <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} spacing={{ base: 4, md: 6 }}>
      <StatCard
        icon={FaUser}
        title="Total Patients"
        value={patientData ? 1 : dbSummary?.total_patients ?? 0}
        color="teal"
        isLoading={!dbSummary && !dbSummaryError}
      />
      <StatCard
        icon={FaCalendarAlt}
        title="Events"
        value={patientData ? patientData.events?.length ?? 0 : 'N/A'}
        color="orange"
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
  ), [patientData, dbSummary, dbSummaryError])

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s" p={{ base: 4, md: 6 }}>
        <Container maxW={containerMaxWidth}>
          <VStack spacing={{ base: 6, md: 8 }} align="stretch">
            <Card bg={cardBgColor} p={{ base: 4, md: 6 }} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h1" size={{ base: "xl", md: "2xl" }} color={primaryColor} mb={4} fontWeight="bold">Clinical Data Dashboard</Heading>
                <Divider mb={4} />
                <Text fontSize={{ base: "md", md: "lg" }} color={textColor} fontWeight="medium">View and analyze patient clinical data.</Text>
              </CardBody>
            </Card>

            {renderSummary}

            <Card bg={cardBgColor} p={{ base: 4, md: 6 }} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h2" size={{ base: "lg", md: "xl" }} color={secondaryColor} mb={{ base: 4, md: 6 }} fontWeight="semibold">Load Patient Data</Heading>
                <Divider mb={{ base: 4, md: 6 }} />
                <Stack direction={{ base: 'column', md: 'row' }} spacing={4} align="center">
                  <InputGroup flex={1}>
                    <InputLeftElement pointerEvents="none">
                      <Icon as={FaSearch} color="gray.400" />
                    </InputLeftElement>
                    <Input
                      value={patientId}
                      onChange={handlePatientIdChange}
                      placeholder="Enter Patient ID..."
                      bg={cardBgColor}
                      borderColor={borderColor}
                      _hover={{ borderColor: primaryColor }}
                      fontSize={{ base: "md", md: "lg" }}
                      height={{ base: "40px", md: "50px" }}
                    />
                  </InputGroup>
                  <Button
                    colorScheme="teal"
                    onClick={loadPatientData}
                    isLoading={isLoading}
                    loadingText="Loading..."
                    size={{ base: "md", md: "lg" }}
                    width={{ base: 'full', md: 'auto' }}
                    height={{ base: "40px", md: "50px" }}
                    fontSize={{ base: "md", md: "lg" }}
                    fontWeight="semibold"
                  >
                    Load Patient Data
                  </Button>
                </Stack>
              </CardBody>
            </Card>

            {patientData && (
              <Card bg={cardBgColor} p={{ base: 4, md: 6 }} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
                <CardBody>
                  <Heading as="h2" size={{ base: "lg", md: "xl" }} color={secondaryColor} mb={{ base: 4, md: 6 }} fontWeight="semibold">Patient Data</Heading>
                  <Divider mb={{ base: 4, md: 6 }} />
                  <Tabs variant="soft-rounded" colorScheme="teal" size={{ base: "md", md: "lg" }}>
                    <TabList mb={{ base: 4, md: 6 }} flexWrap="wrap" gap={4}>
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }} fontWeight="medium">Events</Tab>
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }} fontWeight="medium">Clinical Notes</Tab>
                      <Tab _selected={{ color: 'white', bg: 'teal.500' }} fontWeight="medium">QA Pairs</Tab>
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
            )}
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(HomePage)
