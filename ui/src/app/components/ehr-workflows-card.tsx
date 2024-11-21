import React, { useState } from 'react'
import {
  Card,
  CardBody,
  Heading,
  VStack,
  Button,
  Text,
  useColorModeValue,
  useToast,
  Box,
  Spinner,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react'
import { FaMedkit } from 'react-icons/fa'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface EHRWorkflowsCardProps {
  patientId: string
}

const EHRWorkflowsCard: React.FC<EHRWorkflowsCardProps> = ({ patientId }) => {
  const [isLoading, setIsLoading] = useState(false)
  const [medicationsTable, setMedicationsTable] = useState<string | null>(null)
  const toast = useToast()

  // Color mode values
  const cardBgColor = useColorModeValue('white', 'gray.800')
  const borderColor = useColorModeValue('gray.200', 'gray.600')
  const headerBgColor = useColorModeValue('gray.50', 'gray.700')
  const hoverBgColor = useColorModeValue('blue.50', 'blue.900')
  const textColor = useColorModeValue('gray.800', 'white')

  const handleRetrieveMedications = async () => {
    setIsLoading(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('No token found')

      // Fetch medications
      const medsResponse = await fetch(`/api/patient_data/${patientId}/medications`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'text/plain'
        },
      })

      if (!medsResponse.ok) {
        const errorText = await medsResponse.text()
        throw new Error(`Failed to fetch medications: ${errorText}`)
      }

      const medications = await medsResponse.text()

      if (!medications.trim()) {
        setMedicationsTable("No medications found for this patient.")
        return
      }

      // Format medications into table
      const formatResponse = await fetch('/api/format_medications', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          medications: medications.replace(/^"|"$/g, '')
        }),
      })

      if (!formatResponse.ok) {
        const errorText = await formatResponse.text()
        throw new Error(`Failed to format medications: ${errorText}`)
      }

      const { formatted_medications } = await formatResponse.json()
      setMedicationsTable(formatted_medications)
    } catch (error) {
      console.error('Error:', error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "An error occurred",
        status: "error",
        duration: 3000,
        isClosable: true,
      })
      setMedicationsTable(null)
    } finally {
      setIsLoading(false)
    }
  }

  // Custom components for ReactMarkdown
  const MarkdownComponents = {
    table: ({ children }: { children: React.ReactNode }) => (
      <Table variant="simple" size="sm" width="100%">
        {children}
      </Table>
    ),
    thead: ({ children }: { children: React.ReactNode }) => (
      <Thead bg={headerBgColor}>{children}</Thead>
    ),
    tbody: ({ children }: { children: React.ReactNode }) => (
      <Tbody>{children}</Tbody>
    ),
    tr: ({ children }: { children: React.ReactNode }) => (
      <Tr
        _hover={{ bg: hoverBgColor }}
        transition="background-color 0.2s"
      >
        {children}
      </Tr>
    ),
    th: ({ children }: { children: React.ReactNode }) => (
      <Th
        borderWidth={1}
        borderColor={borderColor}
        p={3}
        textAlign="left"
        color={textColor}
        fontWeight="bold"
      >
        {children}
      </Th>
    ),
    td: ({ children }: { children: React.ReactNode }) => (
      <Td
        borderWidth={1}
        borderColor={borderColor}
        p={3}
        textAlign="left"
        color={textColor}
      >
        {children}
      </Td>
    ),
  }

  return (
    <Card
      bg={cardBgColor}
      shadow="md"
      borderWidth={1}
      borderColor={borderColor}
      transition="transform 0.2s"
      _hover={{ transform: 'translateY(-2px)' }}
    >
      <CardBody>
        <VStack spacing={4} align="stretch">
          <Heading
            as="h3"
            size="md"
            color="#1f5280"
            fontFamily="'Roboto Slab', serif"
          >
            EHR Workflows
          </Heading>

          <Button
            leftIcon={<FaMedkit />}
            colorScheme="blue"
            variant="outline"
            isLoading={isLoading}
            onClick={handleRetrieveMedications}
            size="sm"
            loadingText="Retrieving medications..."
          >
            Retrieve Medications
          </Button>

          {isLoading && (
            <Box textAlign="center" py={4}>
              <Spinner size="sm" mr={2} color="blue.500" />
              <Text display="inline-block" fontSize="sm" color={textColor}>
                Processing medications...
              </Text>
            </Box>
          )}

          {medicationsTable && !isLoading && (
            <Box
              mt={4}
              p={4}
              borderWidth={1}
              borderRadius="md"
              borderColor={borderColor}
              overflowX="auto"
              bg={cardBgColor}
              shadow="sm"
            >
              <Text
                mb={4}
                fontSize="sm"
                fontWeight="bold"
                color="#1f5280"
                borderBottom="2px"
                borderColor="blue.500"
                pb={2}
              >
                Current Medications
              </Text>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={MarkdownComponents}
              >
                {medicationsTable}
              </ReactMarkdown>
            </Box>
          )}
        </VStack>
      </CardBody>
    </Card>
  )
}

export default EHRWorkflowsCard
