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
  Input,
  Container,
  Card,
  CardBody,
  SimpleGrid,
  Icon,
  Select,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  useToast,
  Skeleton,
  InputGroup,
  InputLeftElement,
  Divider,
  Tag,
  Tooltip,
  Badge,
} from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import { FaFileAlt, FaUser, FaHospital, FaSearch, FaEye } from 'react-icons/fa'
import Sidebar from '../components/sidebar'
import { withAuth } from '../components/with-auth'
import { MedicalNote } from '../types/note'

const HomePage: React.FC = () => {
  const [patientId, setPatientId] = useState<string>('')
  const [collection, setCollection] = useState<string>('')
  const [collections, setCollections] = useState<string[]>([])
  const [medicalNotes, setMedicalNotes] = useState<MedicalNote[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isLoadingCollections, setIsLoadingCollections] = useState<boolean>(true)

  const router = useRouter()
  const toast = useToast()

  const primaryColor = useColorModeValue('teal.500', 'teal.300')
  const secondaryColor = useColorModeValue('blue.500', 'blue.300')
  const bgColor = useColorModeValue('gray.50', 'gray.900')
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const textColor = useColorModeValue('gray.800', 'gray.100')
  const borderColor = useColorModeValue('gray.200', 'gray.700')
  const tableBorderColor = useColorModeValue('gray.200', 'gray.600')
  const tableHoverBg = useColorModeValue('gray.100', 'gray.700')
  const tableHeaderBg = useColorModeValue('gray.100', 'gray.700')

  useEffect(() => {
    fetchCollections()
  }, [])

  const fetchCollections = async () => {
    try {
      const response = await fetch('/api/collections', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })
      if (!response.ok) {
        throw new Error('Failed to fetch collections')
      }
      const data = await response.json()
      setCollections(data)
      if (data.length > 0) {
        setCollection(data[0])
      }
    } catch (error) {
      console.error('Error fetching collections:', error)
      toast({
        title: "Error",
        description: "Failed to fetch collections",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
    } finally {
      setIsLoadingCollections(false)
    }
  }

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
      const response = await fetch(`/api/medical_notes/${collection}/${patientId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (response.status === 404) {
        setMedicalNotes([])
        toast({
          title: "Info",
          description: "No clinical notes found for this patient",
          status: "info",
          duration: 3000,
          isClosable: true,
        })
        return
      }

      if (!response.ok) {
        throw new Error('Failed to fetch clinical notes')
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
      console.error('Error loading clinical notes:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred while loading clinical notes",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      setMedicalNotes([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNoteClick = (noteId: string) => {
    router.push(`/note/${collection}/${noteId}`)
  }

  return (
    <Flex minHeight="100vh" bg={bgColor}>
      <Sidebar />
      <Box flex={1} ml={{ base: 0, md: 60 }} transition="margin-left 0.3s" p={6}>
        <Container maxW="container.xl">
          <VStack spacing={8} align="stretch">
            <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h1" size="xl" color={primaryColor} mb={4}>Clinical Notes Dashboard</Heading>
                <Text fontSize="lg" color={textColor}>Load and extract entities from clinical notes.</Text>
              </CardBody>
            </Card>

            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
              <StatCard icon={FaFileAlt} title="Total Notes" value={medicalNotes.length} color="teal" />
              <StatCard icon={FaUser} title="Patient ID" value={patientId || 'N/A'} color="blue" />
              <StatCard icon={FaHospital} title="Collection" value={collection || 'N/A'} color="purple" />
            </SimpleGrid>

            <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h2" size="lg" color={secondaryColor} mb={6}>Load Clinical Notes</Heading>
                <Flex direction={{ base: 'column', md: 'row' }} mb={4} align="center" gap={4}>
                  <Select
                    value={collection}
                    onChange={(e) => setCollection(e.target.value)}
                    isDisabled={isLoadingCollections}
                    bg={cardBgColor}
                    borderColor={borderColor}
                    _hover={{ borderColor: primaryColor }}
                    flex={1}
                  >
                    {isLoadingCollections ? (
                      <option>Loading collections...</option>
                    ) : (
                      collections.map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))
                    )}
                  </Select>
                  <InputGroup flex={1}>
                    <InputLeftElement pointerEvents="none">
                      <Icon as={FaSearch} color="gray.300" />
                    </InputLeftElement>
                    <Input
                      value={patientId}
                      onChange={(e) => setPatientId(e.target.value)}
                      placeholder="Enter Patient ID..."
                      bg={cardBgColor}
                      borderColor={borderColor}
                      _hover={{ borderColor: primaryColor }}
                    />
                  </InputGroup>
                  <Button
                    colorScheme="teal"
                    onClick={loadMedicalNotes}
                    isLoading={isLoading}
                    loadingText="Loading..."
                    size="lg"
                    width={{ base: 'full', md: 'auto' }}
                  >
                    Load Notes
                  </Button>
                </Flex>
              </CardBody>
            </Card>

            <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="lg" borderWidth={1} borderColor={borderColor}>
              <CardBody>
                <Heading as="h2" size="lg" color={secondaryColor} mb={6}>Clinical Notes</Heading>
                {isLoading ? (
                  <VStack spacing={4}>
                    {[...Array(5)].map((_, index) => (
                      <Skeleton key={index} height="60px" width="100%" />
                    ))}
                  </VStack>
                ) : medicalNotes.length > 0 ? (
                  <Box overflowX="auto">
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr bg={tableHeaderBg}>
                          <Th borderColor={tableBorderColor} color={primaryColor}>Note ID</Th>
                          <Th borderColor={tableBorderColor} color={primaryColor}>Patient ID</Th>
                          <Th borderColor={tableBorderColor} color={primaryColor}>Encounter ID</Th>
                          <Th borderColor={tableBorderColor} color={primaryColor}>Timestamp</Th>
                          <Th borderColor={tableBorderColor} color={primaryColor}>Text Preview</Th>
                          <Th borderColor={tableBorderColor} color={primaryColor}>Action</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        {medicalNotes.map((note, index) => (
                          <React.Fragment key={note.note_id}>
                            <Tr _hover={{ bg: tableHoverBg }} transition="background-color 0.2s">
                              <Td borderColor={tableBorderColor}>
                                <Tag colorScheme="blue" variant="solid">{note.note_id}</Tag>
                              </Td>
                              <Td borderColor={tableBorderColor}>
                                <Badge colorScheme="green">{note.patient_id}</Badge>
                              </Td>
                              <Td borderColor={tableBorderColor}>
                                <Badge colorScheme="purple">
                                  {note.encounter_id === '-1' ? 'N/A' : note.encounter_id}
                                </Badge>
                              </Td>
                              <Td borderColor={tableBorderColor}>
                                <Text fontSize="sm" color={textColor}>{new Date(note.timestamp).toLocaleString()}</Text>
                              </Td>
                              <Td borderColor={tableBorderColor}>
                                <Tooltip label={note.text} placement="top" hasArrow>
                                  <Text fontSize="sm" color={textColor} isTruncated maxWidth="200px">
                                    {note.text.substring(0, 50)}...
                                  </Text>
                                </Tooltip>
                              </Td>
                              <Td borderColor={tableBorderColor}>
                                <Button
                                  size="sm"
                                  onClick={() => handleNoteClick(note.note_id)}
                                  colorScheme="blue"
                                  variant="outline"
                                  leftIcon={<FaEye />}
                                >
                                  View
                                </Button>
                              </Td>
                            </Tr>
                            {index < medicalNotes.length - 1 && (
                              <Tr>
                                <Td colSpan={6} p={0}>
                                  <Divider borderColor={tableBorderColor} />
                                </Td>
                              </Tr>
                            )}
                          </React.Fragment>
                        ))}
                      </Tbody>
                    </Table>
                  </Box>
                ) : (
                  <Text color={textColor}>No clinical notes available. Please load notes for a patient.</Text>
                )}
              </CardBody>
            </Card>
          </VStack>
        </Container>
      </Box>
    </Flex>
  )
}

interface StatCardProps {
  icon: React.ElementType;
  title: string;
  value: string | number;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ icon, title, value, color }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.700')

  return (
    <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="md" borderWidth={1} borderColor={borderColor}>
      <CardBody>
        <VStack spacing={4} align="center">
          <Icon as={icon} boxSize={10} color={`${color}.500`} />
          <Heading size="md" textAlign="center">{title}</Heading>
          <Text fontSize="2xl" fontWeight="bold" color={`${color}.500`}>{value}</Text>
        </VStack>
      </CardBody>
    </Card>
  )
}

export default withAuth(HomePage)
