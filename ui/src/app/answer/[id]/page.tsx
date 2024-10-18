'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  useToast, Skeleton, Text, Heading, Progress
} from '@chakra-ui/react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '../../components/sidebar'
import { withAuth } from '../../components/with-auth'
import SearchBox from '../../components/search-box'
import AnswerCard from '../../components/answer-card'
import StepsCard from '../../components/steps-card'

const MotionBox = motion(Box)

interface Step {
  step: string;
  reasoning: string;
}

interface Query {
  query: string;
  patient_id?: number;
  steps?: Step[];
}

interface Answer {
  answer: string;
  reasoning: string;
}

interface QueryAnswer {
  query: Query;
  answer?: Answer;
  is_first: boolean;
}

interface PageData {
  id: string;
  user_id: string;
  query_answers: QueryAnswer[];
  created_at: string;
  updated_at: string;
}

interface SearchState {
  isSearching: boolean;
  steps: Step[];
  answer: string | null;
  reasoning: string | null;
  isGeneratingAnswer: boolean;
}

const AnswerPage: React.FC = () => {
  const [pageData, setPageData] = useState<PageData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [searchState, setSearchState] = useState<SearchState>({
    isSearching: false,
    steps: [],
    answer: null,
    reasoning: null,
    isGeneratingAnswer: false,
  })
  const params = useParams()
  const searchParams = useSearchParams()
  const id = params?.id as string
  const isNewQuery = searchParams?.get('new') === 'true'
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')

  const fetchPageData = useCallback(async (): Promise<PageData | null> => {
    setIsLoading(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch(`/api/pages/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(`Failed to fetch page data: ${errorData.message}`)
      }

      const data: PageData = await response.json()
      setPageData(data)
      return data
    } catch (error) {
      console.error('Error loading page data:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while loading page data",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return null
    } finally {
      setIsLoading(false)
    }
  }, [id, toast])

  const generateStepsAndAnswer = useCallback(async (query: string, pageId: string, patientId?: number): Promise<[Step[], Answer | null]> => {
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      // Generate COT steps
      const stepsResponse = await fetch('/api/generate_cot_steps', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, page_id: pageId, patient_id: patientId }),
      })

      if (!stepsResponse.ok) {
        throw new Error('Failed to generate COT steps')
      }

      const { cot_steps } = await stepsResponse.json()

      // Generate answer only if steps are successful
      if (cot_steps.length > 0) {
        const answerResponse = await fetch('/api/generate_cot_answer', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query, page_id: pageId, patient_id: patientId, steps: cot_steps }),
        })

        if (!answerResponse.ok) {
          throw new Error('Failed to generate answer')
        }

        const answerData = await answerResponse.json()
        return [cot_steps, answerData]
      } else {
        return [cot_steps, null]
      }
    } catch (error) {
      console.error('Error generating steps and answer:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while generating steps and answer",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return [[], null]
    }
  }, [toast])

  useEffect(() => {
    const initializePage = async () => {
      const data = await fetchPageData();
      if (data) {
        const firstQueryAnswer = data.query_answers[0];
        if (firstQueryAnswer) {
          if (isNewQuery && !firstQueryAnswer.query.steps) {
            setSearchState(prev => ({ ...prev, isSearching: true }));
            const [steps, answer] = await generateStepsAndAnswer(firstQueryAnswer.query.query, id, firstQueryAnswer.query.patient_id);
            setSearchState(prev => ({
              ...prev,
              steps,
              answer: answer?.answer || null,
              reasoning: answer?.reasoning || null,
              isGeneratingAnswer: false,
              isSearching: false
            }));
            if (steps.length > 0 && answer) {
              setPageData(prevData => {
                if (!prevData) return data;
                const updatedQueryAnswers = [
                  { ...firstQueryAnswer, query: { ...firstQueryAnswer.query, steps }, answer },
                  ...prevData.query_answers.slice(1)
                ];
                return { ...prevData, query_answers: updatedQueryAnswers };
              });
            }
          } else {
            // Handle existing page data
            setSearchState(prev => ({
              ...prev,
              steps: firstQueryAnswer.query.steps || [],
              answer: firstQueryAnswer.answer?.answer || null,
              reasoning: firstQueryAnswer.answer?.reasoning || null,
              isGeneratingAnswer: false,
              isSearching: false
            }));
          }
        }
      }
    };

    initializePage();
  }, [fetchPageData, generateStepsAndAnswer, isNewQuery, id]);

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

    setSearchState({
      isSearching: true,
      steps: [],
      answer: null,
      reasoning: null,
      isGeneratingAnswer: false,
    })

    try {
      const [steps, answer] = await generateStepsAndAnswer(query, id)

      setSearchState(prev => ({
        ...prev,
        steps,
        answer: answer?.answer || null,
        reasoning: answer?.reasoning || null,
        isGeneratingAnswer: false,
        isSearching: false
      }))

      if (steps.length > 0 && answer) {
        // Update the page data with the new query, steps, and answer
        setPageData(prevData => {
          if (!prevData) return null
          const updatedQueryAnswers = [
            ...prevData.query_answers,
            {
              query: { query, steps },
              answer,
              is_first: false
            }
          ]
          return { ...prevData, query_answers: updatedQueryAnswers }
        })
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
    }
  }, [generateStepsAndAnswer, id, toast])

  const firstQueryAnswer = pageData?.query_answers[0]
  const { isSearching, steps, answer, reasoning, isGeneratingAnswer } = searchState

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
                        {steps.length > 0 ? "Generating Answer" : "Generating Steps"}
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
                        {steps.length > 0
                          ? "Synthesizing information and formulating response..."
                          : "Analyzing query and formulating reasoning steps..."}
                      </Text>
                    </CardBody>
                  </Card>
                </MotionBox>
              )}
            </AnimatePresence>

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
              {answer && (
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

            <Box>
              <SearchBox onSearch={handleSearch} isLoading={isSearching || isGeneratingAnswer} />
            </Box>
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(AnswerPage)
