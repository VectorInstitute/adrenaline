'use client'

import React, { useState, useCallback, useMemo } from 'react'
import {
  Box, Heading, Text, VStack, useColorModeValue, Flex, Divider, Skeleton,
  Card, CardHeader, CardBody, Badge, Button, useToast, HStack, Stat,
  StatLabel, StatNumber, StatGroup, IconButton, Tooltip, Container,
} from '@chakra-ui/react'
import { useParams } from 'next/navigation'
import useSWR from 'swr'
import Sidebar from '../../../components/sidebar'
import { withAuth } from '../../../components/with-auth'
import EntityVisualization from '../../../components/entity-viz'
import { CopyIcon } from '@chakra-ui/icons'
import { ClinicalNote, NERResponse } from '../../../types/patient'

const fetcher = async (url: string): Promise<ClinicalNote> => {
  const token = localStorage.getItem('token')
  if (!token) throw new Error('No token found')

  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
  if (!res.ok) {
    throw new Error('Failed to fetch note')
  }
  return res.json()
}

function NotePage() {
  const params = useParams()
  const { patientId, noteId } = params as { patientId: string; noteId: string }
  const { data: note, error, isLoading } = useSWR<ClinicalNote>(
    patientId && noteId ? `/api/patient/${patientId}/note/${noteId}` : null,
    fetcher
  )
  const [nerResponse, setNerResponse] = useState<NERResponse | null>(null)
  const [isExtracting, setIsExtracting] = useState(false)
  const [isCopying, setIsCopying] = useState(false)
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const cardBgColor = useColorModeValue('white', 'gray.700')
  const noteBgColor = useColorModeValue('gray.100', 'gray.800')

  const extractEntities = useCallback(async () => {
    if (!patientId || !noteId) return

    setIsExtracting(true)
    setNerResponse(null)

    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch(`/api/extract_entities/${patientId}/${noteId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Failed to extract entities: ${response.status} ${response.statusText}\n${errorText}`)
      }

      const data: NERResponse = await response.json()

      if (!data.entities || !Array.isArray(data.entities)) {
        throw new Error('Invalid response format: entities is missing or not an array')
      }

      setNerResponse(data)

      toast({
        title: "Success",
        description: `Extracted ${data.entities.length} entities successfully`,
        status: "success",
        duration: 3000,
        isClosable: true,
      })
    } catch (error) {
      console.error('Error extracting entities:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to extract entities",
        status: "error",
        duration: 5000,
        isClosable: true,
      })
    } finally {
      setIsExtracting(false)
    }
  }, [patientId, noteId, toast])

  const resetNote = useCallback(() => {
    setNerResponse(null)
  }, [])

  const copyToClipboard = useCallback(async () => {
    if (!patientId || !noteId) return

    setIsCopying(true)

    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      const response = await fetch(`/api/patient/${patientId}/note/${noteId}/raw`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch raw note')
      }

      const rawNote = await response.text()

      if (!rawNote) {
        throw new Error('Raw note text is empty')
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(rawNote)
      } else {
        const textArea = document.createElement('textarea')
        textArea.value = rawNote
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
      }

      toast({
        title: "Copied",
        description: "Raw note text copied to clipboard",
        status: "success",
        duration: 2000,
        isClosable: true,
      })
    } catch (error) {
      console.error('Failed to copy text: ', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to copy text to clipboard",
        status: "error",
        duration: 2000,
        isClosable: true,
      })
    } finally {
      setIsCopying(false)
    }
  }, [patientId, noteId, toast])

  const entityStats = useMemo(() => {
    if (!nerResponse) return [];
    const groups = nerResponse.entities.reduce((acc, entity) => {
      entity.types.forEach(type => {
        acc[type] = (acc[type] || 0) + 1;
      });
      return acc;
    }, {} as Record<string, number>);
    return Object.entries(groups).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [nerResponse]);

  const renderContent = () => {
    if (isLoading) {
      return (
        <VStack spacing={8} align="stretch">
          <Skeleton height="40px" />
          <Skeleton height="20px" />
          <Skeleton height="20px" />
          <Skeleton height="400px" />
        </VStack>
      )
    }

    if (error) {
      return <Text color="red.500">Error loading note: {error.message}</Text>
    }

    if (!note) {
      return <Text>Note not found</Text>
    }

    return (
      <Card bg={cardBgColor} shadow="md">
        <CardHeader>
          <Heading size="md">Clinical Note Details</Heading>
        </CardHeader>
        <CardBody>
          <VStack align="stretch" spacing={6}>
            <Flex wrap="wrap" gap={2}>
              <Badge colorScheme="blue">Note ID: {note.note_id}</Badge>
              <Badge colorScheme="green">Patient ID: {patientId}</Badge>
              <Badge colorScheme="purple">Encounter ID: {note.encounter_id}</Badge>
              <Badge colorScheme="cyan">Timestamp: {new Date(note.timestamp).toLocaleString()}</Badge>
              <Badge colorScheme="orange">Note Type: {note.note_type}</Badge>
            </Flex>
            <Divider />
            <HStack spacing={4}>
              <Button
                onClick={extractEntities}
                isLoading={isExtracting}
                loadingText="Extracting..."
                colorScheme="teal"
              >
                {nerResponse ? 'Re-extract Entities' : 'Extract Entities'}
              </Button>
              {nerResponse && (
                <Button onClick={resetNote} colorScheme="gray">
                  Reset Note
                </Button>
              )}
            </HStack>
            {nerResponse && (
              <StatGroup>
                <Stat>
                  <StatLabel>Total Entities</StatLabel>
                  <StatNumber>{nerResponse.entities.length}</StatNumber>
                </Stat>
                {entityStats.map(([group, count]) => (
                  <Stat key={group}>
                    <StatLabel>{group}</StatLabel>
                    <StatNumber>{count}</StatNumber>
                  </Stat>
                ))}
              </StatGroup>
            )}
            <Box position="relative" bg={noteBgColor} p={4} borderRadius="md" shadow="sm">
              <Tooltip label="Copy raw note to clipboard">
                <IconButton
                  aria-label="Copy raw note to clipboard"
                  icon={<CopyIcon />}
                  onClick={copyToClipboard}
                  isLoading={isCopying}
                  size="md"
                  position="absolute"
                  top={2}
                  right={2}
                  zIndex={1}
                  colorScheme="teal"
                />
              </Tooltip>
              {isExtracting ? (
                <Skeleton height="200px" />
              ) : nerResponse ? (
                <EntityVisualization text={nerResponse.text} entities={nerResponse.entities} />
              ) : (
                <Text whiteSpace="pre-wrap" fontSize="sm">{note.text}</Text>
              )}
            </Box>
          </VStack>
        </CardBody>
      </Card>
    )
  }

  return (
    <Flex direction={{ base: 'column', md: 'row' }} minHeight="100vh" bg={bgColor} color={textColor}>
      <Sidebar />
      <Box flex={1} p={4} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s" overflowX="hidden">
        <Container maxW="container.xl">
          {renderContent()}
        </Container>
      </Box>
    </Flex>
  )
}

export default withAuth(NotePage)
