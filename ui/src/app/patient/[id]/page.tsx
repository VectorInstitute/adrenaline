'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import {
  Box,
  Flex,
  VStack,
  useColorModeValue,
  Container,
  Card,
  CardBody,
  useToast,
  Skeleton,
  Text,
  Grid,
  GridItem,
  Progress,
  Heading,
} from '@chakra-ui/react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '../../components/sidebar'
import { withAuth } from '../../components/with-auth'
import { PatientData } from '../../types/patient'
import PatientSummaryCard from '../../components/patient-summary-card'
import PatientDetailsCard from '../../components/patient-details-card'
import PatientEncountersTable from '../../components/patient-encounters-table'
import SearchBox from '../../components/search-box'
import AnswerCard from '../../components/answer-card'
import EHRWorkflowsCard from '../../components/ehr-workflows-card'

const MotionBox = motion(Box)

interface SearchState {
  isSearching: boolean
  answer: string | null
  reasoning: string | null
  pageId: string | null
}

const PatientPage: React.FC = () => {
  const [patientData, setPatientData] = useState<PatientData | null>(null)
  const [encounters, setEncounters] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isLoadingEncounters, setIsLoadingEncounters] = useState<boolean>(true)
  const [searchState, setSearchState] = useState<SearchState>({
    isSearching: false,
    answer: null,
    reasoning: null,
    pageId: null,
  })
  const { id } = useParams<{ id: string }>()
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')

  const fetchEncounters = useCallback(async () => {
    setIsLoadingEncounters(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch(`/api/patient_data/encounters/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch encounters')
      }

      const data = await response.json()
      setEncounters(data)
    } catch (error) {
      console.error('Error loading encounters:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while loading encounters",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setIsLoadingEncounters(false)
    }
  }, [id, toast])

  const fetchPatientData = useCallback(async () => {
    setIsLoading(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch(`/api/patient_data/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch patient data')
      }

      const data: PatientData = await response.json()
      setPatientData(data)
    } catch (error) {
      console.error('Error loading patient data:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while loading patient data",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setIsLoading(false)
    }
  }, [id, toast])

  useEffect(() => {
    Promise.all([fetchPatientData(), fetchEncounters()])
  }, [fetchPatientData, fetchEncounters])

  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      toast({
        title: "Error",
        description: "Please enter a query",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return
    }

    setSearchState(prev => ({ ...prev, isSearching: true, answer: null, reasoning: null }))

    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const createPageResponse = await fetch('/api/pages/create', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, patient_id: Number(id) }),
      })

      if (!createPageResponse.ok) {
        const errorData = await createPageResponse.json()
        throw new Error(`Failed to create new page: ${JSON.stringify(errorData)}`)
      }

      const { page_id } = await createPageResponse.json()
      setSearchState(prev => ({ ...prev, pageId: page_id }))

      const answerResponse = await fetch('/api/generate_answer', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, patient_id: Number(id), page_id }),
      })

      if (!answerResponse.ok) {
        throw new Error('Failed to generate answer')
      }

      const answerData = await answerResponse.json()
      setSearchState(prev => ({
        ...prev,
        answer: answerData.answer,
        reasoning: answerData.reasoning,
        isSearching: false,
      }))

    } catch (error) {
      console.error('Error:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      setSearchState(prev => ({ ...prev, isSearching: false }))
    }
  }, [id, toast])

  const { isSearching, answer, reasoning, pageId } = searchState

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 72 }} transition="margin-left 0.3s" p={{ base: 4, md: 4 }}>
        <Container maxW="container.xl" px={0}>
          <VStack spacing={6} align="stretch" justify="center" minHeight="100vh">
            <Grid templateColumns={{ base: "1fr", md: "1fr 2fr" }} gap={6}>
              <GridItem>
                <VStack spacing={6} align="stretch">
                  <MotionBox
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                  >
                    {isLoading ? (
                      <Skeleton height="200px" />
                    ) : patientData ? (
                      <PatientSummaryCard patientData={patientData} />
                    ) : (
                      <Card bg={cardBgColor} shadow="md">
                        <CardBody>
                          <Text>No patient data found</Text>
                        </CardBody>
                      </Card>
                    )}
                  </MotionBox>

                  <MotionBox
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                  >
                  {isLoading ? (
                      <Skeleton height="200px" />
                    ) : patientData ? (
                      <PatientEncountersTable encounters={encounters} />
                    ) : (
                      <Card bg={cardBgColor} shadow="md">
                        <CardBody>
                          <Text>No patient data found</Text>
                        </CardBody>
                      </Card>
                    )}
                  </MotionBox>

                  <MotionBox
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                  >
                  {isLoading ? (
                      <Skeleton height="200px" />
                    ) : patientData ? (
                      <EHRWorkflowsCard patientId={id} />
                    ) : (
                      <Card bg={cardBgColor} shadow="md">
                        <CardBody>
                          <Text>No patient data found</Text>
                        </CardBody>
                      </Card>
                    )}
                  </MotionBox>

                  <SearchBox onSearch={handleSearch} isLoading={isSearching} isPatientPage={true} />

                  <AnimatePresence>
                    {isSearching && (
                      <MotionBox
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.5 }}
                      >
                        <Card bg={cardBgColor} shadow="md">
                          <CardBody>
                            <Heading as="h3" size="md" mb={4} fontFamily="'Roboto Slab', serif">
                              Generating Answer
                            </Heading>
                            <Progress
                              size="xs"
                              isIndeterminate
                              colorScheme="blue"
                              sx={{
                                '& > div': {
                                  transitionDuration: '1.5s',
                                },
                              }}
                            />
                            <Text mt={2} fontFamily="'Roboto Slab', serif">
                              Analyzing query and formulating response...
                            </Text>
                          </CardBody>
                        </Card>
                      </MotionBox>
                    )}
                  </AnimatePresence>

                  <AnimatePresence>
                    {pageId && answer && (
                      <MotionBox
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.5 }}
                      >
                        <AnswerCard answer={answer} reasoning={reasoning} isLoading={isSearching} />
                      </MotionBox>
                    )}
                  </AnimatePresence>
                </VStack>
              </GridItem>
              <GridItem>
                <MotionBox
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                >
                  {isLoading ? (
                    <Skeleton height="500px" />
                  ) : patientData ? (
                    <PatientDetailsCard patientData={patientData} patientId={id} />
                  ) : null}
                </MotionBox>
              </GridItem>
            </Grid>
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(PatientPage)
