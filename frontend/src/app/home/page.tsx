'use client'
import React, { useState, useEffect } from 'react'
import {
  Box,
  Text,
  Flex,
  Heading,
  VStack,
  useColorModeValue,
  Button,
  Textarea,
  Input,
  Container,
  Divider,
} from '@chakra-ui/react'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'

function HomePage() {
  const [medicalNote, setMedicalNote] = useState('')
  const [userPrompt, setUserPrompt] = useState('')
  const [response, setResponse] = useState('')

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const accentColor = useColorModeValue('blue.500', 'blue.300')

  useEffect(() => {
    // Load a sample medical note or fetch from an API
    const sampleNote = "Patient presents with..."
    setMedicalNote(sampleNote)
  }, [])

  const handleSubmit = async () => {
    // Combine the medical note and user prompt
    const combinedPrompt = `Medical Note: ${medicalNote}\n\nUser Query: ${userPrompt}`

    // Send to LLM backend endpoint
    try {
      const result = await sendToLLM(combinedPrompt)
      setResponse(result)
    } catch (error) {
      console.error('Error querying LLM:', error)
      setResponse('An error occurred while processing your request.')
    }
  }

  const sendToLLM = async (prompt) => {
    // Implement your LLM API call here
    // This is a placeholder function
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve('This is a sample response from the LLM.')
      }, 1000)
    })
  }

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s">
        <Container maxW="container.xl" py={8}>
          <VStack spacing={8} align="stretch">
            <Box bg={cardBgColor} p={8} borderRadius="lg" shadow="md">
              <Heading as="h1" size="xl" color={textColor} mb={4}>Clinical LLM Dataset Curation</Heading>
              <Text fontSize="lg" color={textColor}>Create and curate question-answer pairs for clinical LLMs.</Text>
            </Box>
            <Divider />
            <Box bg={cardBgColor} p={8} borderRadius="lg" shadow="md">
              <Heading as="h2" size="lg" color={textColor} mb={4}>Medical Note</Heading>
              <Textarea
                value={medicalNote}
                onChange={(e) => setMedicalNote(e.target.value)}
                placeholder="Enter or load medical note here..."
                size="lg"
                minHeight="200px"
                mb={4}
              />
              <Heading as="h2" size="lg" color={textColor} mb={4}>User Prompt</Heading>
              <Input
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                placeholder="Enter your question or instruction..."
                size="lg"
                mb={4}
              />
              <Button colorScheme="blue" onClick={handleSubmit}>Submit</Button>
            </Box>
            {response && (
              <Box bg={cardBgColor} p={8} borderRadius="lg" shadow="md">
                <Heading as="h2" size="lg" color={textColor} mb={4}>LLM Response</Heading>
                <Text>{response}</Text>
              </Box>
            )}
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(HomePage)
