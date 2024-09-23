'use client'

import React, { useState, useCallback } from 'react'
import {
  Box, Flex, VStack, useColorModeValue, Container, Card, CardBody,
  Heading, useToast
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import { PatientData } from '../types/patient'
import PatientCard from '../components/patient-card'
import PatientTable from '../components/patient-table'
import SearchBar from '../components/search-bar'

const HomePage: React.FC = () => {
  const [patientData, setPatientData] = useState<PatientData | PatientData[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const router = useRouter()
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('teal.200', 'teal.700')

  const searchPatients = useCallback(async (query: string) => {
    if (!query.trim()) {
      toast({
        title: "Error",
        description: "Please enter a query or patient ID",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return
    }

    setIsLoading(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      let response: Response
      const patientIdNumber = Number(query)
      if (!isNaN(patientIdNumber)) {
        response = await fetch(`/api/patient_data/${patientIdNumber}`, {
          headers: { 'Authorization': `Bearer ${token}` },
        })

        if (response.status === 404) {
          setPatientData([])
          toast({
            title: "Info",
            description: "No data found for this patient",
            status: "info",
            duration: 3000,
            isClosable: true,
          })
          return
        }

        const data: PatientData = await response.json()
        setPatientData(data)
      } else {
        response = await fetch('/api/retrieve', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query }),
        })

        const data: PatientData[] = await response.json()
        setPatientData(data)
      }

      toast({
        title: "Success",
        description: "Patient data loaded successfully",
        status: "success",
        duration: 3000,
        isClosable: true,
      })
    } catch (error) {
      console.error('Error loading patient data:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while loading patient data",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      setPatientData([])
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  const handleNoteClick = useCallback((patientId: string, noteId: string) => {
    router.push(`/note/${patientId}/${noteId}`)
  }, [router])

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s" p={{ base: 4, md: 6 }}>
        <Container maxW="container.xl" px={0}>
          <VStack spacing={6} align="stretch" justify="center" minHeight="100vh">
            <Heading as="h1" size="xl" mb={8} textAlign="center" color="teal.600">
              Where Patient Discovery Begins
            </Heading>
            <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="md" borderWidth={1} borderColor={borderColor} _hover={{ shadow: 'lg' }} transition="all 0.3s">
              <CardBody>
                <SearchBar onSearch={searchPatients} isLoading={isLoading} />
              </CardBody>
            </Card>

            {Array.isArray(patientData) && patientData.length > 0 ? (
              <Card p={4} borderRadius="xl" shadow="md" borderWidth={1} borderColor={borderColor}>
                <CardBody>
                  <PatientTable patients={patientData} />
                </CardBody>
              </Card>
            ) : !Array.isArray(patientData) && patientData.patient_id ? (
              <PatientCard
                patientData={patientData}
                handleNoteClick={(noteId) => handleNoteClick(patientData.patient_id.toString(), noteId)}
              />
            ) : null}
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(HomePage)
