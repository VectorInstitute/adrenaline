'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  useToast, Text, Heading, SimpleGrid, Skeleton
} from '@chakra-ui/react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from '../../components/sidebar'
import { withAuth } from '../../components/with-auth'
import SearchBox from '../../components/search-box'
import PatientCohortCard from '../../components/patient-cohort-card'

const MotionBox = motion(Box)

interface CohortSearchResult {
  patient_id: number;
  note_text: string;
  similarity_score: number;
}

interface GroupedCohortResult {
  patient_id: number;
  total_notes: number;
  notes_summary: CohortSearchResult[];
}

const CohortPage: React.FC = () => {
  const [searchResults, setSearchResults] = useState<GroupedCohortResult[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const id = params?.id as string
  const initialQuery = searchParams?.get('query')
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')

  const performCohortSearch = useCallback(async (query: string): Promise<void> => {
    setIsLoading(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch('/api/cohort_search', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, top_k: 2 }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(`Failed to perform cohort search: ${errorData.message}`)
      }

      const results: CohortSearchResult[] = await response.json()

      const groupedResults = results.reduce((acc, result) => {
        const existingPatient = acc.find(p => p.patient_id === result.patient_id)
        if (existingPatient) {
          existingPatient.total_notes += 1
          existingPatient.notes_summary.push(result)
        } else {
          acc.push({
            patient_id: result.patient_id,
            total_notes: 1,
            notes_summary: [result]
          })
        }
        return acc
      }, [] as GroupedCohortResult[])

      setSearchResults(groupedResults)
    } catch (error) {
      console.error('Error performing cohort search:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while performing cohort search",
        status: "error",
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

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

    await performCohortSearch(query)
  }, [performCohortSearch, toast])

  useEffect(() => {
    if (initialQuery) {
      performCohortSearch(initialQuery)
    }
  }, [initialQuery, performCohortSearch])

  const handlePatientClick = useCallback((patientId: number) => {
    router.push(`/patient/${patientId}`)
  }, [router])

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
              <Card bg={cardBgColor} shadow="md">
                <CardBody>
                  <Heading as="h2" size="lg" mb={4} fontFamily="'Roboto Slab', serif">Cohort Search</Heading>
                  <Text fontFamily="'Roboto Slab', serif" fontSize="lg">{initialQuery || "Enter a query to search across all patients"}</Text>
                </CardBody>
              </Card>
            </MotionBox>

            <AnimatePresence>
              <MotionBox
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5 }}
              >
                {isLoading ? (
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                    {[...Array(6)].map((_, index) => (
                      <Skeleton key={index} height="200px" />
                    ))}
                  </SimpleGrid>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                    {searchResults.map((result) => (
                      <PatientCohortCard
                        key={result.patient_id}
                        patientId={result.patient_id}
                        totalNotes={result.total_notes}
                        notes={result.notes_summary}
                        onCardClick={handlePatientClick}
                      />
                    ))}
                  </SimpleGrid>
                )}
              </MotionBox>
            </AnimatePresence>

            <Box>
              <SearchBox onSearch={handleSearch} isLoading={isLoading} isCohortPage={true} />
            </Box>
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(CohortPage)
