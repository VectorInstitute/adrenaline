'use client'

import React, { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  useToast, Skeleton, Text, Heading, Progress
} from '@chakra-ui/react'
import { motion, MotionProps } from 'framer-motion'
import Sidebar from '../../components/sidebar'
import { withAuth } from '../../components/with-auth'
import SearchBox from '../../components/search-box'
import AnswerCard from '../../components/answer-card'
import StepsCard from '../../components/steps-card'

const MotionBox = motion<Omit<React.ComponentProps<typeof Box> & MotionProps, "transition">>(Box)

interface QueryAnswer {
  query: {
    query: string;
    patient_id?: number;
    steps?: Array<{ step: string; reasoning: string }>;
  };
  answer?: {
    answer: string;
    reasoning: string;
  };
  is_first: boolean;
}

interface PageData {
  id: string;
  user_id: string;
  query_answers: QueryAnswer[];
  created_at: string;
  updated_at: string;
}

const AnswerPage: React.FC = () => {
  const [pageData, setPageData] = useState<PageData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isGeneratingSteps, setIsGeneratingSteps] = useState<boolean>(false)
  const [isGeneratingAnswer, setIsGeneratingAnswer] = useState<boolean>(false)
  const params = useParams()
  const id = params?.id as string
  const router = useRouter()
  const toast = useToast()

  const generationStartedRef = useRef(false)

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')

  const generateStepsAndAnswer = useCallback(async (query: string, patientId?: number) => {
    if (generationStartedRef.current) return
    generationStartedRef.current = true
    setIsGeneratingSteps(true)

    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      // Generate steps
      const stepsResponse = await fetch('/api/generate_cot_steps', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, patient_id: patientId }),
      })

      if (!stepsResponse.ok) {
        throw new Error('Failed to generate steps')
      }

      const stepsData = await stepsResponse.json()

      setPageData(prevData => {
        if (!prevData) return null
        const updatedQueryAnswers = prevData.query_answers.map(qa => {
          if (qa.is_first) {
            return { ...qa, query: { ...qa.query, steps: stepsData.cot_steps } }
          }
          return qa
        })
        return { ...prevData, query_answers: updatedQueryAnswers }
      })

      setIsGeneratingSteps(false)
      setIsGeneratingAnswer(true)

      // Generate answer
      const answerResponse = await fetch('/api/generate_cot_answer', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          patient_id: patientId,
          steps: stepsData.cot_steps
        }),
      })

      if (!answerResponse.ok) {
        throw new Error('Failed to generate answer')
      }

      const answerData = await answerResponse.json()

      setPageData(prevData => {
        if (!prevData) return null
        const updatedQueryAnswers = prevData.query_answers.map(qa => {
          if (qa.is_first) {
            return { ...qa, answer: answerData }
          }
          return qa
        })
        return { ...prevData, query_answers: updatedQueryAnswers }
      })

    } catch (error) {
      console.error('Error:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while generating steps and answer",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setIsGeneratingSteps(false)
      setIsGeneratingAnswer(false)
    }
  }, [toast])

  useEffect(() => {
    const fetchPageData = async () => {
      setIsLoading(true)
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('No token found')

        const response = await fetch(`/api/pages/${id}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        })

        if (!response.ok) {
          throw new Error('Failed to fetch page data')
        }

        const data: PageData = await response.json()
        setPageData(data)
        setIsLoading(false)

        const firstQueryAnswer = data.query_answers.find(qa => qa.is_first)
        if (firstQueryAnswer && !firstQueryAnswer.query.steps) {
          await generateStepsAndAnswer(firstQueryAnswer.query.query, firstQueryAnswer.query.patient_id)
        }
      } catch (error) {
        console.error('Error loading page data:', error)
        toast({
          title: "Error",
          description: error instanceof Error ? error.message : "An error occurred while loading page data",
          status: "error",
          duration: 3000,
          isClosable: true,
        })
        setIsLoading(false)
      }
    }

    if (id) {
      fetchPageData()
    }

    return () => {
      generationStartedRef.current = false
    }
  }, [id, generateStepsAndAnswer, toast])

  const handleSearch = async (query: string) => {
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

    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const createPageResponse = await fetch('/api/pages/create', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      })

      if (!createPageResponse.ok) {
        throw new Error('Failed to create new page')
      }

      const { page_id } = await createPageResponse.json()

      router.push(`/answer/${page_id}`)
    } catch (error) {
      console.error('Error:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
    }
  }

  const firstQueryAnswer = pageData?.query_answers.find(qa => qa.is_first)

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 72 }} transition="margin-left 0.3s" p={{ base: 4, md: 6 }}>
        <Container maxW="container.xl" px={0}>
          <VStack spacing={6} align="stretch" justify="center" minHeight="100vh">
            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              {isLoading ? (
                <Skeleton height="100px" />
              ) : firstQueryAnswer ? (
                <Card bg={cardBgColor} shadow="md">
                  <CardBody>
                    <Heading as="h2" size="lg" mb={4} fontFamily="'Roboto Slab', serif">Query</Heading>
                    <Text fontFamily="'Roboto Slab', serif" fontSize="lg">{firstQueryAnswer.query.query}</Text>
                  </CardBody>
                </Card>
              ) : (
                <Card bg={cardBgColor} shadow="md">
                  <CardBody>
                    <Text fontFamily="'Roboto Slab', serif">No page data found</Text>
                  </CardBody>
                </Card>
              )}
            </MotionBox>

            {!isLoading && (
              <>
                {(isGeneratingSteps || isGeneratingAnswer) && (
                  <MotionBox
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                  >
                    <Card bg={cardBgColor} shadow="md">
                      <CardBody>
                        <Heading as="h3" size="md" mb={4} fontFamily="'Roboto Slab', serif">
                          {isGeneratingSteps ? "Generating Steps" : "Generating Answer"}
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
                          {isGeneratingSteps
                            ? "Analyzing query and formulating reasoning steps..."
                            : "Synthesizing information and formulating response..."}
                        </Text>
                      </CardBody>
                    </Card>
                  </MotionBox>
                )}

                {firstQueryAnswer?.query.steps && (
                  <MotionBox
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                  >
                    <StepsCard steps={firstQueryAnswer.query.steps} />
                  </MotionBox>
                )}

                {firstQueryAnswer?.answer && !isGeneratingAnswer && (
                  <MotionBox
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.5 }}
                  >
                    <AnswerCard
                      answer={firstQueryAnswer.answer.answer}
                      reasoning={firstQueryAnswer.answer.reasoning}
                    />
                  </MotionBox>
                )}
              </>
            )}

            {!pageData && (
              <Box>
                <SearchBox onSearch={handleSearch} isLoading={isLoading} />
              </Box>
            )}
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(AnswerPage)
