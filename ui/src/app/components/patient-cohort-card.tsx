// ui/src/app/components/PatientCohortCard.tsx
import React from 'react';
import {
  Box, Card, CardBody, Heading, Badge, Text, useColorModeValue,
  Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon,
  VStack, StackDivider
} from '@chakra-ui/react';

interface Note {
  note_text: string;
  similarity_score: number;
}

interface PatientCohortCardProps {
  patientId: number;
  totalNotes: number;
  notes: Note[];
  onCardClick: (patientId: number) => void;
}

const PatientCohortCard: React.FC<PatientCohortCardProps> = ({ patientId, totalNotes, notes, onCardClick }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800');
  const noteBgColor = useColorModeValue('gray.50', 'gray.700');

  return (
    <Card
      bg={cardBgColor}
      shadow="md"
      cursor="pointer"
      onClick={() => onCardClick(patientId)}
      _hover={{ transform: 'scale(1.02)', transition: 'transform 0.2s' }}
    >
      <CardBody>
        <Heading as="h3" size="md" mb={2} fontFamily="'Roboto Slab', serif">
          Patient ID: {patientId}
        </Heading>
        <Badge colorScheme="blue" mb={2}>Total Notes: {totalNotes}</Badge>
        <Accordion allowToggle>
          <AccordionItem border="none">
            <AccordionButton pl={0} onClick={(e) => e.stopPropagation()}>
              <Box flex="1" textAlign="left">
                <Text fontWeight="bold">View Matching Notes</Text>
              </Box>
              <AccordionIcon />
            </AccordionButton>
            <AccordionPanel pb={4}>
              <VStack
                divider={<StackDivider borderColor="gray.200" />}
                spacing={4}
                align="stretch"
              >
                {notes.map((note, index) => (
                  <Box key={index} p={3} bg={noteBgColor} borderRadius="md">
                    <Text noOfLines={3} mb={2}>{note.note_text}</Text>
                    <Text fontSize="sm" color="blue.500" fontWeight="bold">
                      Similarity Score: {note.similarity_score.toFixed(4)}
                    </Text>
                  </Box>
                ))}
              </VStack>
            </AccordionPanel>
          </AccordionItem>
        </Accordion>
      </CardBody>
    </Card>
  );
};

export default PatientCohortCard;
