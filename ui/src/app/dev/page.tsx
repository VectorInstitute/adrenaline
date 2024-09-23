'use client'

import React from 'react'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  SimpleGrid, Heading, Text, useBreakpointValue, Spinner
} from '@chakra-ui/react'
import { FaFileAlt, FaUser, FaQuestionCircle, FaCalendarAlt } from 'react-icons/fa'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import useSWR from 'swr'
import StatCard from '../components/stat-card'

interface DatabaseSummary {
  total_patients: number;
  total_notes: number;
  total_qa_pairs: number;
  total_events: number | 'N/A';
}

const fetcher = async (url: string): Promise<DatabaseSummary> => {
  const token = localStorage.getItem('token')
  if (!token) throw new Error('No token found')

  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
  if (!res.ok) throw new Error('Failed to fetch data')
  return res.json()
}

const DevPage: React.FC = () => {
  const { data: dbSummary, error: dbSummaryError } = useSWR<DatabaseSummary>('/api/database_summary', fetcher, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    refreshInterval: 300000,
  })

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')
  const textColor = useColorModeValue('gray.600', 'gray.300')

  const containerMaxWidth = useBreakpointValue({ base: '100%', sm: 'container.sm', md: 'container.md', lg: 'container.xl' })

  const renderSummary = () => (
    <SimpleGrid columns={{ base: 1, sm: 2, md: 4 }} spacing={6}>
      <StatCard
        icon={FaUser}
        title="Total Patients"
        value={dbSummary?.total_patients ?? 0}
        color="teal"
        isLoading={!dbSummary && !dbSummaryError}
      />
      <StatCard
        icon={FaFileAlt}
        title="Total Notes"
        value={dbSummary?.total_notes ?? 0}
        color="blue"
        isLoading={!dbSummary && !dbSummaryError}
      />
      <StatCard
        icon={FaQuestionCircle}
        title="Total QA Pairs"
        value={dbSummary?.total_qa_pairs ?? 0}
        color="purple"
        isLoading={!dbSummary && !dbSummaryError}
      />
      <StatCard
        icon={FaCalendarAlt}
        title="Total Events"
        value={dbSummary?.total_events ?? 'N/A'}
        color="orange"
        isLoading={!dbSummary && !dbSummaryError}
      />
    </SimpleGrid>
  )

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s" p={{ base: 4, md: 6 }}>
        <Container maxW={containerMaxWidth}>
          <VStack spacing={8} align="stretch">
            <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h1" size="xl" mb={4} textAlign="center">
                  Database Summary
                </Heading>
                <Text fontSize="lg" mb={6} textAlign="center" color={textColor}>
                  Overview of the patient database
                </Text>
                {dbSummaryError ? (
                  <Text color="red.500" textAlign="center">Error loading database summary</Text>
                ) : !dbSummary ? (
                  <Flex justify="center">
                    <Spinner size="xl" />
                  </Flex>
                ) : (
                  renderSummary()
                )}
              </CardBody>
            </Card>
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(DevPage)
