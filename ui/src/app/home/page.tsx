'use client'

import React, { useState, useCallback } from 'react'
import {
  Box, Flex, VStack, useColorModeValue, Container, Heading, useToast
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import SearchBox from '../components/search-box'

const HomePage: React.FC = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const router = useRouter()
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')

  const handleSearch = useCallback(async (query: string, isPatientMode: boolean) => {
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

      if (isPatientMode) {
        const patientId = Number(query)
        if (isNaN(patientId)) {
          throw new Error('Invalid patient ID')
        }
        router.push(`/patient/${patientId}`)
      } else {
        const response = await fetch('/api/generate_cot_answer', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query }),
        })

        if (!response.ok) {
          throw new Error('Failed to generate answer')
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('Failed to read response')

        let pageId: string | null = null

        const decoder = new TextDecoder()
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'page_id') {
                pageId = data.content
                break
              }
            }
          }
          if (pageId) break
        }

        if (pageId) {
          router.push(`/answer/${pageId}`)
        } else {
          throw new Error('Failed to get page ID')
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
      setIsLoading(false)
    }
  }, [router, toast])

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 72 }} transition="margin-left 0.3s" p={{ base: 5, md: 7 }}>
        <Container maxW="container.xl" px={0} display="flex" flexDirection="column" justifyContent="center" alignItems="center" height="100%">
          <VStack spacing={7} align="center" justify="center" width="100%">
            <Heading as="h1" size="2xl" mb={10} textAlign="center" color="#1f5280" fontFamily="'Roboto Slab', serif">
              Where Patient Discovery Begins
            </Heading>
            <SearchBox onSearch={handleSearch} isLoading={isLoading} />
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(HomePage)
