'use client'

import React, { useState, useCallback, useMemo } from 'react'
import {
  Box,
  Heading,
  Text,
  VStack,
  useColorModeValue,
  Flex,
  Divider,
  Skeleton,
  Card,
  CardHeader,
  CardBody,
  Badge,
  Button,
  useToast,
  HStack,
  Stat,
  StatLabel,
  StatNumber,
  StatGroup,
} from '@chakra-ui/react'
import { useParams } from 'next/navigation'
import { MedicalNote } from '../../types/note'
import useSWR from 'swr'
import Sidebar from '../../components/sidebar'
import { withAuth } from '../../components/with-auth'
import EntityVisualization from '../../components/entity-viz'

const fetcher = async (url: string) => {
  const res = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
  })
  if (!res.ok) {
    throw new Error('Failed to fetch note')
  }
  return res.json()
}

interface Entity {
  entity_group: string
  word: string
  start: number
  end: number
  score: number
}

interface NERResponse {
  note_id: string
  text: string
  entities: Entity[]
}

function NotePage() {
  const params = useParams()
  const { noteId } = params
  const { data: note, error, isLoading } = useSWR<MedicalNote>(
    noteId ? `/api/medical_notes/note/${noteId}` : null,
    fetcher
  )
  const [nerResponse, setNerResponse] = useState<NERResponse | null>(null)
  const [isExtracting, setIsExtracting] = useState(false)
  const toast = useToast()

  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const cardBgColor = useColorModeValue('white', 'gray.700')

  const extractEntities = useCallback(async () => {
    if (!noteId) return

    setIsExtracting(true)
    setNerResponse(null)

    try {
      const response = await fetch(`/api/extract_entities/${noteId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Failed to extract entities: ${response.status} ${response.statusText}\n${errorText}`)
      }

      const data: NERResponse = await response.json()
      console.log('NER Response:', data)

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
  }, [noteId, toast])

  const resetNote = useCallback(() => {
    setNerResponse(null)
  }, [])

  const entityStats = useMemo(() => {
    if (!nerResponse) return []
    const groups = nerResponse.entities.reduce((acc, entity) => {
      acc[entity.entity_group] = (acc[entity.entity_group] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    return Object.entries(groups).sort((a, b) => b[1] - a[1]).slice(0, 5)
  }, [nerResponse])

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
      <Card bg={cardBgColor}>
        <CardHeader>
          <Heading size="md">Medical Note Details</Heading>
        </CardHeader>
        <CardBody>
          <VStack align="stretch" spacing={4}>
            <Flex wrap="wrap" gap={2}>
              <Badge colorScheme="blue">Note ID: {note.note_id}</Badge>
              <Badge colorScheme="green">Subject ID: {note.subject_id}</Badge>
              <Badge colorScheme="purple">HADM ID: {note.hadm_id}</Badge>
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
            <Box>
              {isExtracting ? (
                <Skeleton height="200px" />
              ) : nerResponse ? (
                <EntityVisualization text={nerResponse.text} entities={nerResponse.entities} />
              ) : (
                <Text whiteSpace="pre-wrap">{note.text}</Text>
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
        {renderContent()}
      </Box>
    </Flex>
  )
}

export default withAuth(NotePage)
