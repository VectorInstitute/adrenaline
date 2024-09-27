'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  useToast, Skeleton, Text, Heading
} from '@chakra-ui/react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '../../components/sidebar'
import { withAuth } from '../../components/with-auth'
import SearchBox from '../../components/search-box'
import AnswerCard from '../../components/answer-card'
import StepsCard from '../../components/steps-card'

const MotionBox = motion(Box)

interface PageData {
  original_query: string;
  responses: Array<{
    answer: string;
    created_at: string;
  }>;
  follow_ups: Array<any>;
}

const AnswerPage: React.FC = () => {
  const [pageData, setPageData] = useState<PageData | null>(null)
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
    const fetchPageData = async () => {
      setIsLoading(true)
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('No token found')

        const response = await fetch(`/api/page_data/${id}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        })

        if (!response.ok) {
          throw new Error('Failed to fetch page data')
        }

        const data: PageData = await response.json()
        setPageData(data)
        setAnswer(data.responses[0]?.answer || null)
      } catch (error) {
        console.error('Error loading page data:', error)
        toast({
          title: "Error",
          description: error instanceof Error ? error.message : "An error occurred while loading page data",
          status: "error",
          duration: 3000,
          isClosable: true,
        })
      } finally {
        setIsLoading(false)
      }
    }

    fetchPageData()
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
            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              {isLoading ? (
                <Skeleton height="100px" />
              ) : pageData ? (
                <Card bg={cardBgColor} shadow="md">
                  <CardBody>
                    <Heading as="h2" size="lg" mb={4}>Original Query</Heading>
                    <Text>{pageData.original_query}</Text>
                  </CardBody>
                </Card>
              ) : (
                <Card bg={cardBgColor} shadow="md">
                  <CardBody>
                    <Text>No page data found</Text>
                  </CardBody>
                </Card>
              )}
            </MotionBox>
            <Box>
              <SearchBox onSearch={handleSearch} isLoading={isSearching} />
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
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(AnswerPage)
