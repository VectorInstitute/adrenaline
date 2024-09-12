import React from 'react';
import { Card, CardBody, VStack, Icon, Heading, Text, Badge, Wrap, WrapItem, Center, Skeleton, useColorModeValue } from '@chakra-ui/react';
import { FaFileAlt } from 'react-icons/fa';
import { PatientData } from '../types/patient';

interface ClinicalNotesCardProps {
  patientData: PatientData | null;
  dbTotalNotes: number;
  isLoading: boolean;
}

const ClinicalNotesCard: React.FC<ClinicalNotesCardProps> = ({ patientData, dbTotalNotes, isLoading }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const renderContent = () => {
    if (isLoading) {
      return <Skeleton height="24px" width="60px" />;
    }

    if (patientData) {
      const noteCounts = patientData.notes.reduce((acc, note) => {
        acc[note.note_type] = (acc[note.note_type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      return (
        <VStack align="center" spacing={2} width="100%">
          <Text fontSize="2xl" fontWeight="bold" color="blue.500">
            {patientData.notes.length}
          </Text>
          <Wrap justify="center" spacing={2}>
            {Object.entries(noteCounts).map(([type, count]) => (
              <WrapItem key={type}>
                <Badge colorScheme="blue" fontSize="sm" px={2} py={1} borderRadius="full">
                  {type}: {count}
                </Badge>
              </WrapItem>
            ))}
          </Wrap>
        </VStack>
      );
    }

    return (
      <Text fontSize="2xl" fontWeight="bold" color="blue.500">
        {dbTotalNotes}
      </Text>
    );
  };

  return (
    <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="md" borderWidth={1} borderColor={borderColor}>
      <CardBody>
        <VStack spacing={4} align="center">
          <Icon as={FaFileAlt} boxSize={10} color="blue.500" />
          <Heading size="md" textAlign="center">Clinical Notes</Heading>
          <Center width="100%">
            {renderContent()}
          </Center>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default ClinicalNotesCard;
