'use client'

import React, { useEffect, useState, useCallback, useMemo } from 'react'
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

const MotionBox = motion(Box)

interface Query {
  query: string;
  patient_id?: number;
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
  answer: string | null;
  reasoning: string | null;
}

const AnswerPage: React.FC = () => {
  const [pageData, setPageData] = useState<PageData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [searchState, setSearchState] = useState<SearchState>({
    isSearching: false,
    answer: null,
    reasoning: null,
  })
  const params = useParams()
  const searchParams = useSearchParams()
  const id = params?.id as string
  const isNewQuery = searchParams?.get('new') === 'true'
  const initialQuery = searchParams?.get('query')
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

  const generateAnswer = useCallback(async (query: string, pageId: string, patientId?: number): Promise<Answer | null> => {
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const answerResponse = await fetch('/api/generate_cot_answer', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, page_id: pageId, patient_id: patientId }),
        signal: AbortSignal.timeout(180000) // 3 minutes timeout
      })

      if (!answerResponse.ok) {
        const errorData = await answerResponse.json()
        throw new Error(`Failed to generate answer: ${errorData.message || answerResponse.statusText}`)
      }

      return await answerResponse.json()
    } catch (error) {
      console.error('Error generating answer:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while generating answer",
        status: "error",
        duration: 30000,
        isClosable: true,
      })
      return null
    }
  }, [toast])

  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      toast({
        title: "Error",
        description: "Please enter a query",
        status: "error",
        duration: 30000,
        isClosable: true,
      })
      return
    }

    setSearchState(prev => ({ ...prev, isSearching: true, answer: null, reasoning: null }))

    try {
      const answer = await generateAnswer(query, id)

      setSearchState(prev => ({
        ...prev,
        answer: answer?.answer || null,
        reasoning: answer?.reasoning || null,
        isSearching: false
      }))

      if (answer) {
        setPageData(prevData => {
          if (!prevData) return null
          const updatedQueryAnswers = [
            ...prevData.query_answers,
            {
              query: { query },
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
        duration: 30000,
        isClosable: true,
      })
      setSearchState(prev => ({ ...prev, isSearching: false }))
    }
  }, [generateAnswer, id, toast])

  useEffect(() => {
    const initializePage = async () => {
      try {
        const data = await fetchPageData();
        if (data) {
          const firstQueryAnswer = data.query_answers[0];
          if (firstQueryAnswer && isNewQuery && initialQuery && !firstQueryAnswer.answer) {
            setSearchState(prev => ({ ...prev, isSearching: true }));
            const answer = await generateAnswer(initialQuery, id, firstQueryAnswer.query.patient_id);
            setSearchState(prev => ({
              ...prev,
              answer: answer?.answer || null,
              reasoning: answer?.reasoning || null,
              isSearching: false
            }));
            if (answer) {
              setPageData(prevData => {
                if (!prevData) return data;
                const updatedQueryAnswers = prevData.query_answers.map((qa, index) =>
                  index === 0 ? { ...qa, answer } : qa
                );
                return { ...prevData, query_answers: updatedQueryAnswers };
              });
            }
          } else if (firstQueryAnswer && firstQueryAnswer.answer) {
            setSearchState(prev => ({
              ...prev,
              answer: firstQueryAnswer.answer?.answer || null,
              reasoning: firstQueryAnswer.answer?.reasoning || null,
              isSearching: false
            }));
          }
        }
      } catch (error) {
        console.error('Error initializing page:', error);
        toast({
          title: "Error",
          description: "Failed to initialize page. Please try refreshing.",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
        setSearchState(prev => ({ ...prev, isSearching: false }));
      }
    };

    initializePage();
  }, [fetchPageData, generateAnswer, isNewQuery, initialQuery, id, toast]);

  const firstQueryAnswer = useMemo(() => pageData?.query_answers[0], [pageData]);
  const { isSearching, answer, reasoning } = searchState;

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
              {answer && (
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

            <Box>
              <SearchBox onSearch={handleSearch} isLoading={isSearching} />
            </Box>
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(AnswerPage)
