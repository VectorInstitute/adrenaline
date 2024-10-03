'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  useToast, Skeleton, Text, Heading, Divider, Badge, HStack
} from '@chakra-ui/react'
import { motion, MotionProps } from 'framer-motion'
import { FiClock } from 'react-icons/fi'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import { formatDistanceToNow, subHours } from 'date-fns'

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
  const textColor = useColorModeValue('gray.600', 'gray.300')
  const highlightColor = useColorModeValue('blue.500', 'blue.300')

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

  const convertToLocalTime = (utcDateString: string): string => {
    const utcDate = new Date(utcDateString)
    const adjustedDate = subHours(utcDate, 5)  // 5 hours behind UTC
    return adjustedDate.toLocaleString()
  }

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 72 }} transition="margin-left 0.3s" p={{ base: 4, md: 6 }}>
        <Container maxW="container.xl" px={0}>
          <HStack spacing={2} mb={2}>
            <FiClock size={24} color={highlightColor} />
            <Heading as="h1" size="xl" color={highlightColor} fontFamily="'Roboto Slab', serif">History</Heading>
          </HStack>
          <Divider mb={6} borderColor={borderColor} />
          <VStack spacing={6} align="stretch">
            {isLoading ? (
              Array(5).fill(0).map((_, i) => (
                <Skeleton key={i} height="120px" borderRadius="md" />
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
                    _hover={{ boxShadow: 'md', borderColor: highlightColor }}
                    transition="all 0.2s"
                  >
                    <CardBody>
                      <Flex justifyContent="space-between" alignItems="flex-start" mb={2}>
                        <Text fontSize="lg" fontWeight="bold" color={highlightColor} fontFamily="'Roboto Slab', serif">
                          {page.query_answers[0]?.query.query}
                        </Text>
                        <Badge colorScheme="blue">
                          {formatDistanceToNow(subHours(new Date(page.created_at), 5), { addSuffix: true })}
                        </Badge>
                      </Flex>
                      <Text fontSize="sm" color={textColor} mb={3} fontFamily="'Roboto Slab', serif">
                        Created: {convertToLocalTime(page.created_at)}
                      </Text>
                      {page.query_answers[0]?.answer && (
                        <>
                          <Divider my={3} borderColor={borderColor} />
                          <Text fontSize="md" noOfLines={2} color={textColor} fontFamily="'Roboto Slab', serif">
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
