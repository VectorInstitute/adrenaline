'use client'

import React, { useState, useCallback } from 'react'
import {
  Box, Flex, VStack, useColorModeValue, Container, Heading, useToast
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import SearchBox from '../components/search-box'

interface CreatePageResponse {
  page_id: string;
}

const HomePage: React.FC = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const router = useRouter()
  const toast = useToast()

  const bgGradient = useColorModeValue(
    'linear(to-br, blue.50, blue.100, blue.200)',
    'linear(to-br, gray.900, gray.800, gray.700)'
  )

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
        const createPageResponse = await fetch('/api/pages/create', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ query }),
        })

        if (!createPageResponse.ok) {
          const errorData = await createPageResponse.json();
          throw new Error(`Failed to create new page: ${JSON.stringify(errorData)}`);
        }

        const { page_id }: CreatePageResponse = await createPageResponse.json()

        if (page_id) {
          router.push(`/answer/${page_id}?new=true`)
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
    <Flex minHeight="100vh">
      <Sidebar />
      <Box
        flex={1}
        ml={{ base: 0, md: 60 }} // Adjust this value to match your sidebar width
        position="relative"
        overflow="hidden"
        bgGradient={bgGradient}
      >
        <Box
          position="absolute"
          top="-15%"
          right="-7%"
          width="95%"
          height="120%"
          bg={useColorModeValue('blue.50', 'gray.800')}
          transform="rotate(15deg)"
          boxShadow="xl"
          borderRadius="30% 0 0 70%"
          zIndex="0"
        />
        <Container
          maxW="container.xl"
          px={0}
          display="flex"
          flexDirection="column"
          justifyContent="center"
          alignItems="center"
          height="100vh"
          position="relative"
          zIndex="1"
        >
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
