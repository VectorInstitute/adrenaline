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
import { subHours, differenceInMinutes, differenceInHours, differenceInDays, differenceInWeeks } from 'date-fns'

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

const UTC_OFFSET = 4
const TOAST_DURATION = 3000

const usePageHistory = () => {
  const [pages, setPages] = useState<PageData[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<Error | null>(null)
  const toast = useToast()

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

        const data = await response.json() as PageData[]
        setPages(data)
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "An unknown error occurred"
        console.error('Error loading page history:', errorMessage)
        setError(error instanceof Error ? error : new Error(errorMessage))
        toast({
          title: "Error",
          description: errorMessage,
          status: "error",
          duration: TOAST_DURATION,
          isClosable: true,
        })
      } finally {
        setIsLoading(false)
      }
    }

    fetchPageHistory()
  }, [toast])

  return { pages, isLoading, error }
}

const convertToLocalTime = (utcDateString: string): string => {
  const utcDate = new Date(utcDateString)
  const adjustedDate = subHours(utcDate, UTC_OFFSET)
  return adjustedDate.toLocaleString()
}

const formatTimeAgo = (dateString: string): string => {
  const date = subHours(new Date(dateString), UTC_OFFSET)
  const now = new Date()
  const minutesDiff = differenceInMinutes(now, date)
  const hoursDiff = differenceInHours(now, date)
  const daysDiff = differenceInDays(now, date)
  const weeksDiff = differenceInWeeks(now, date)

  if (minutesDiff < 1) {
    return 'Just now'
  } else if (minutesDiff < 60) {
    return `${minutesDiff} minute${minutesDiff !== 1 ? 's' : ''} ago`
  } else if (hoursDiff < 24) {
    return `${hoursDiff} hour${hoursDiff !== 1 ? 's' : ''} ago`
  } else if (daysDiff < 7) {
    return `${daysDiff} day${daysDiff !== 1 ? 's' : ''} ago`
  } else {
    return `${weeksDiff} week${weeksDiff !== 1 ? 's' : ''} ago`
  }
}

const HistoryCard: React.FC<{ page: PageData; onClick: () => void }> = ({ page, onClick }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')
  const textColor = useColorModeValue('gray.600', 'gray.300')
  const highlightColor = useColorModeValue('blue.500', 'blue.300')

  return (
    <Card
      bg={cardBgColor}
      borderColor={borderColor}
      borderWidth="1px"
      boxShadow="sm"
      _hover={{ boxShadow: 'md', borderColor: highlightColor }}
      transition="all 0.2s"
      onClick={onClick}
      cursor="pointer"
    >
      <CardBody>
        <Flex justifyContent="space-between" alignItems="flex-start" mb={2}>
          <Text fontSize="lg" fontWeight="bold" color={highlightColor} fontFamily="'Roboto Slab', serif">
            {page.query_answers[0]?.query.query}
          </Text>
          <Badge colorScheme="blue">
            {formatTimeAgo(page.created_at)}
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
  )
}

const HistoryPage: React.FC = () => {
  const { pages, isLoading } = usePageHistory()
  const router = useRouter()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const borderColor = useColorModeValue('gray.200', 'gray.700')
  const highlightColor = useColorModeValue('blue.500', 'blue.300')

  const handlePageCardClick = (pageId: string) => {
    router.push(`/answer/${pageId}`)
  }

  return (
    <Flex direction={{ base: "column", md: "row" }} minHeight="100vh" bg={bgColor}>
      <Sidebar display={{ base: "none", md: "block" }} />
      <Box flex={1} ml={{ base: 0, md: 72 }} transition="margin-left 0.3s" p={{ base: 4, md: 6, lg: 8 }}>
        <Container maxW={{ base: "100%", md: "container.xl" }} px={{ base: 2, md: 0 }}>
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
                >
                  <HistoryCard page={page} onClick={() => handlePageCardClick(page.id)} />
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
