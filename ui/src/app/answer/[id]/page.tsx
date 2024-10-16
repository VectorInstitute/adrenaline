'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
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

const AnswerPage: React.FC = () => {
  const [pageData, setPageData] = useState<PageData | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isGeneratingSteps, setIsGeneratingSteps] = useState<boolean>(false)
  const [isGeneratingAnswer, setIsGeneratingAnswer] = useState<boolean>(false)
  const params = useParams()
  const searchParams = useSearchParams()
  const id = params?.id as string
  const isNewQuery = searchParams?.get('new') === 'true'
  const router = useRouter()
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


  const generateSteps = useCallback(async (query: string, pageId: string, patientId?: number): Promise<Step[] | null> => {
    setIsGeneratingSteps(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No token found');

      const stepsResponse = await fetch('/api/generate_cot_steps', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, page_id: pageId, patient_id: patientId }),
      });

      if (!stepsResponse.ok) {
        const errorData = await stepsResponse.json();
        throw new Error(`Failed to generate steps: ${errorData.message}`);
      }

      const stepsData = await stepsResponse.json();
      return stepsData.cot_steps;
    } catch (error) {
      console.error('Error generating steps:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while generating steps",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return null;
    } finally {
      setIsGeneratingSteps(false);
    }
  }, [toast]);

  const generateAnswer = useCallback(async (query: string, pageId: string, patientId?: number, steps?: Step[]): Promise<Answer | null> => {
    setIsGeneratingAnswer(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No token found');

      const answerResponse = await fetch('/api/generate_cot_answer', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          page_id: pageId,
          patient_id: patientId,
          steps
        }),
      });

      if (!answerResponse.ok) {
        const errorData = await answerResponse.json();
        throw new Error(`Failed to generate answer: ${errorData.message}`);
      }

      const answerData = await answerResponse.json();
      return answerData;
    } catch (error) {
      console.error('Error generating answer:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while generating the answer",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return null;
    } finally {
      setIsGeneratingAnswer(false);
    }
  }, [toast]);

  const [hasGeneratedAnswer, setHasGeneratedAnswer] = useState<boolean>(false)

  useEffect(() => {
    const initializePage = async () => {
      const data = await fetchPageData();
      if (data && isNewQuery) {
        const firstQueryAnswer = data.query_answers[0];
        if (firstQueryAnswer && !firstQueryAnswer.query.steps) {
          const steps = await generateSteps(firstQueryAnswer.query.query, id, firstQueryAnswer.query.patient_id);
          if (steps) {
            const answer = await generateAnswer(firstQueryAnswer.query.query, id, firstQueryAnswer.query.patient_id, steps);
            if (answer) {
              setPageData(prevData => {
                if (!prevData) return data;
                const updatedQueryAnswers = [
                  { ...firstQueryAnswer, query: { ...firstQueryAnswer.query, steps }, answer },
                  ...prevData.query_answers.slice(1)
                ];
                return { ...prevData, query_answers: updatedQueryAnswers };
              });
            }
          }
        }
      }
    };

    initializePage();
  }, [fetchPageData, generateSteps, generateAnswer, isNewQuery, id]);

  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      toast({
        title: "Error",
        description: "Please enter a query",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error('No token found');

      // Append the new query to the existing page
      const appendResponse = await fetch(`/api/pages/${id}/append`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: query }),
      });

      if (!appendResponse.ok) {
        const errorData = await appendResponse.json();
        throw new Error(`Failed to append to page: ${errorData.message}`);
      }

      // Generate steps for the new query
      setIsGeneratingSteps(true);
      const steps = await generateSteps(query, id);
      setIsGeneratingSteps(false);

      if (steps) {
        // Generate answer using the steps
        setIsGeneratingAnswer(true);
        const answer = await generateAnswer(query, id, undefined, steps);
        setIsGeneratingAnswer(false);

        if (answer) {
          // Update the page data with the new query, steps, and answer
          setPageData(prevData => {
            if (!prevData) return null;
            const updatedQueryAnswers = [
              ...prevData.query_answers,
              {
                query: { query, steps },
                answer,
                is_first: false
              }
            ];
            return { ...prevData, query_answers: updatedQueryAnswers };
          });
        }
      }
    } catch (error) {
      console.error('Error:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const firstQueryAnswer = pageData?.query_answers[0]

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

            <Box>
              <SearchBox onSearch={handleSearch} isLoading={isLoading || isGeneratingSteps || isGeneratingAnswer} />
            </Box>
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(AnswerPage)
