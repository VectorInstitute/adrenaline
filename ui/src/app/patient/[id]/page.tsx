'use client'

import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { useParams } from 'next/navigation'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  useToast, Skeleton, Text, Grid, GridItem
} from '@chakra-ui/react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '../../components/sidebar'
import { withAuth } from '../../components/with-auth'
import { PatientData } from '../../types/patient'
import PatientSummaryCard from '../../components/patient-summary-card'
import PatientDetailsCard from '../../components/patient-details-card'
import SearchBox from '../../components/search-box'
import AnswerCard from '../../components/answer-card'
import StepsCard from '../../components/steps-card'

const MotionBox = motion(Box)

interface Step {
  step: string
  reasoning: string
}

interface SearchState {
  isSearching: boolean
  steps: Step[]
  answer: string | null
  reasoning: string | null
  isGeneratingAnswer: boolean
}

const PatientPage: React.FC = () => {
  const [patientData, setPatientData] = useState<PatientData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [searchState, setSearchState] = useState<SearchState>({
    isSearching: false,
    steps: [],
    answer: null,
    reasoning: null,
    isGeneratingAnswer: false,
  })
  const { id } = useParams<{ id: string }>()
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')

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
    fetchPatientData()
  }, [fetchPatientData])

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

    setSearchState(prev => ({ ...prev, isSearching: true, steps: [], answer: null, reasoning: null, isGeneratingAnswer: false }))

    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch('/api/generate_cot_answer', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, patient_id: id }),
      })

      if (!response.ok) {
        throw new Error('Failed to generate answer')
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('Failed to read response')

      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            switch (data.type) {
              case 'step':
                setSearchState(prev => ({ ...prev, steps: [...prev.steps, data.content] }))
                break
              case 'answer':
                setSearchState(prev => ({
                  ...prev,
                  isGeneratingAnswer: true,
                  answer: data.content.answer,
                  reasoning: data.content.reasoning
                }))
                break
              case 'error':
                throw new Error(data.content)
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setSearchState(prev => ({ ...prev, isSearching: false, isGeneratingAnswer: false }))
    }
  }, [id, toast])

  const { isSearching, steps, answer, reasoning, isGeneratingAnswer } = searchState

  const renderPatientSummary = useMemo(() => (
    isLoading ? (
      <Skeleton height="200px" />
    ) : patientData ? (
      <PatientSummaryCard patientData={patientData} />
    ) : (
      <Card bg={cardBgColor} shadow="md">
        <CardBody>
          <Text>No patient data found</Text>
        </CardBody>
      </Card>
    )
  ), [isLoading, patientData, cardBgColor])

  const renderPatientDetails = useMemo(() => (
    isLoading ? (
      <Skeleton height="500px" />
    ) : patientData ? (
      <PatientDetailsCard patientData={patientData} patientId={id} />
    ) : null
  ), [isLoading, patientData, id])

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 72 }} transition="margin-left 0.3s" p={{ base: 4, md: 6 }}>
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
                    {renderPatientSummary}
                  </MotionBox>
                  <SearchBox onSearch={handleSearch} isLoading={isSearching} isPatientPage={true} />
                  <AnimatePresence>
                    {steps.length > 0 && (
                      <MotionBox
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.5 }}
                      >
                        <StepsCard steps={steps} isGeneratingAnswer={isGeneratingAnswer} />
                      </MotionBox>
                    )}
                  </AnimatePresence>
                  <AnimatePresence>
                    {(isGeneratingAnswer || answer) && (
                      <MotionBox
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.5 }}
                      >
                        <AnswerCard answer={answer} reasoning={reasoning} isLoading={isGeneratingAnswer} />
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
                  {renderPatientDetails}
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
