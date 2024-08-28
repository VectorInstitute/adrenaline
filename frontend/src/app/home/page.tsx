'use client'
import React, { useState } from 'react'
import {
  Box,
  Text,
  Flex,
  Heading,
  VStack,
  useColorModeValue,
  Button,
  Input,
  Container,
  Divider,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useToast,
} from '@chakra-ui/react'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'

interface MedicalNote {
  note_id: string;
  subject_id: number;
  hadm_id: string;
  text: string;
}

function HomePage() {
  const [patientId, setPatientId] = useState('')
  const [medicalNotes, setMedicalNotes] = useState<MedicalNote[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const textColor = useColorModeValue('gray.800', 'gray.100')

  const toast = useToast()

  const loadMedicalNotes = async () => {
    if (!patientId.trim()) {
      toast({
        title: "Error",
        description: "Please enter a patient ID",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return
    }

    // Validate that patientId is a number
    if (isNaN(Number(patientId))) {
      toast({
        title: "Error",
        description: "Patient ID must be a number",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      return
    }

    setIsLoading(true)
    try {
      const response = await fetch(`/api/medical_notes/${patientId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('No medical notes found for this patient')
        } else {
          throw new Error('Failed to fetch medical notes')
        }
      }

      const data = await response.json()
      setMedicalNotes(data)
      toast({
        title: "Success",
        description: "Medical notes loaded successfully",
        status: "success",
        duration: 3000,
        isClosable: true,
      })
    } catch (error) {
      console.error('Error loading medical notes:', error)
      toast({
        title: "Error",
        description: error.message || "An error occurred while loading medical notes",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      setMedicalNotes([])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s">
        <Container maxW="container.xl" py={8}>
          <VStack spacing={8} align="stretch">
            <Box bg={cardBgColor} p={8} borderRadius="lg" shadow="md">
              <Heading as="h1" size="xl" color={textColor} mb={4}>Medical Notes Dashboard</Heading>
              <Text fontSize="lg" color={textColor}>Load and view medical notes for a specific patient.</Text>
            </Box>
            <Divider />
            <Box bg={cardBgColor} p={8} borderRadius="lg" shadow="md">
              <Heading as="h2" size="lg" color={textColor} mb={4}>Load Medical Notes</Heading>
              <Flex>
                <Input
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  placeholder="Enter patient ID..."
                  size="lg"
                  mr={4}
                />
                <Button colorScheme="blue" onClick={loadMedicalNotes} isLoading={isLoading}>
                  Load Notes
                </Button>
              </Flex>
            </Box>
            {medicalNotes.length > 0 && (
              <Box bg={cardBgColor} p={8} borderRadius="lg" shadow="md">
                <Heading as="h2" size="lg" color={textColor} mb={4}>Medical Notes</Heading>
                <Table variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Note ID</Th>
                      <Th>Subject ID</Th>
                      <Th>HADM ID</Th>
                      <Th>Text</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {medicalNotes.map((note) => (
                      <Tr key={note.note_id}>
                        <Td>{note.note_id}</Td>
                        <Td>{note.subject_id}</Td>
                        <Td>{note.hadm_id}</Td>
                        <Td>{note.text.substring(0, 100)}...</Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            )}
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(HomePage)
