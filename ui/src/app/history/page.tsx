'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  useToast, Skeleton, Text, Heading, Divider
} from '@chakra-ui/react'
import { motion, MotionProps } from 'framer-motion'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'

const MotionBox = motion<Omit<React.ComponentProps<typeof Box> & MotionProps, "transition">>(Box)

interface PageData {
  id: string;
  user_id: string;
  query_answers: Array<{
    query: {
      query: string;
      patient_id?: number;
    };
    answer?: {
      answer: string;
      reasoning: string;
    };
    is_first: boolean;
  }>;
  created_at: string;
  updated_at: string;
}

const HistoryPage: React.FC = () => {
  const [pages, setPages] = useState<PageData[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const router = useRouter()
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')

  useEffect(() => {
    const fetchPageHistory = async () => {
      setIsLoading(true)
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('No token found')

        const response = await fetch('/api/pages/history', {
          headers: { 'Authorization': `Bearer ${token}` },
        })

        if (!response.ok) {
          throw new Error('Failed to fetch page history')
        }

        const data: PageData[] = await response.json()
        setPages(data)
      } catch (error) {
        console.error('Error loading page history:', error)
        toast({
          title: "Error",
          description: error instanceof Error ? error.message : "An error occurred while loading page history",
          status: "error",
          duration: 3000,
          isClosable: true,
        })
      } finally {
        setIsLoading(false)
      }
    }

    fetchPageHistory()
  }, [toast])

  const handleCardClick = (pageId: string) => {
    router.push(`/answer/${pageId}`)
  }

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 72 }} transition="margin-left 0.3s" p={{ base: 4, md: 6 }}>
        <Container maxW="container.xl" px={0}>
          <Heading as="h1" size="xl" mb={6}>Query History</Heading>
          <VStack spacing={4} align="stretch">
            {isLoading ? (
              Array(5).fill(0).map((_, i) => (
                <Skeleton key={i} height="100px" />
              ))
            ) : (
              pages.map((page, index) => (
                <MotionBox
                  key={page.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  onClick={() => handleCardClick(page.id)}
                  cursor="pointer"
                >
                  <Card
                    bg={cardBgColor}
                    borderColor={borderColor}
                    borderWidth="1px"
                    boxShadow="sm"
                    _hover={{ boxShadow: 'md' }}
                    transition="all 0.2s"
                  >
                    <CardBody>
                      <Text fontSize="lg" fontWeight="bold" mb={2}>
                        {page.query_answers[0]?.query.query}
                      </Text>
                      <Text fontSize="sm" color="gray.500" mb={2}>
                        Created: {new Date(page.created_at).toLocaleString()}
                      </Text>
                      {page.query_answers[0]?.answer && (
                        <>
                          <Divider my={2} />
                          <Text fontSize="md" noOfLines={2}>
                            {page.query_answers[0].answer.answer}
                          </Text>
                        </>
                      )}
                    </CardBody>
                  </Card>
                </MotionBox>
              ))
            )}
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(HistoryPage)
