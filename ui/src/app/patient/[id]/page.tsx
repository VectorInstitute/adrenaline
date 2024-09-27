'use client'

import React, { useEffect, useState, useCallback } from 'react'
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

const PatientPage: React.FC = () => {
  const [patientData, setPatientData] = useState<PatientData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isSearching, setIsSearching] = useState<boolean>(false)
  const [steps, setSteps] = useState<Array<{ step: string; reasoning: string }>>([])
  const [answer, setAnswer] = useState<string | null>(null)
  const [reasoning, setReasoning] = useState<string | null>(null)
  const [isGeneratingAnswer, setIsGeneratingAnswer] = useState<boolean>(false)
  const { id } = useParams()
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')

  useEffect(() => {
    const fetchPatientData = async () => {
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
    }

    fetchPatientData()
  }, [id, toast])

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

    setIsSearching(true)
    setSteps([])
    setAnswer(null)
    setReasoning(null)
    setIsGeneratingAnswer(false)

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
                setSteps(prevSteps => [...prevSteps, data.content])
                break
              case 'answer':
                setIsGeneratingAnswer(true)
                setAnswer(data.content.answer)
                setReasoning(data.content.reasoning)
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
      setIsSearching(false)
      setIsGeneratingAnswer(false)
    }
  }, [id, toast])

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
                  <Box>
                    <SearchBox onSearch={handleSearch} isLoading={isSearching} isPatientPage={true} />
                  </Box>
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
                  {isLoading ? (
                    <Skeleton height="500px" />
                  ) : patientData ? (
                    <PatientDetailsCard patientData={patientData} patientId={id as string} />
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
