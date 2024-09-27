import React from 'react';
import { Box, Text, useColorModeValue, Skeleton, VStack, Divider } from '@chakra-ui/react';

interface AnswerCardProps {
  answer: string | null;
  reasoning: string | null;
  isLoading: boolean;
}

const AnswerCard: React.FC<AnswerCardProps> = ({ answer, reasoning, isLoading }) => {
  const bgColor = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('blue.100', 'blue.700');
  const headerBgColor = useColorModeValue('blue.50', 'blue.900');

  return (
    <Box
      bg={bgColor}
      borderWidth={2}
      borderColor={borderColor}
      borderRadius="md"
      overflow="hidden"
      shadow="lg"
    >
      <Box bg={headerBgColor} p={4}>
        <Text fontWeight="bold" fontSize="lg">Clinical Response</Text>
      </Box>
      <VStack align="stretch" spacing={4} p={4}>
        <Box>
          <Text fontWeight="bold" mb={2} color="blue.500">Answer:</Text>
          {isLoading ? (
            <Skeleton height="100px" />
          ) : (
            <Text>{answer}</Text>
          )}
        </Box>
        <Divider />
        <Box>
          <Text fontWeight="bold" mb={2} color="blue.500">Reasoning:</Text>
          {isLoading ? (
            <Skeleton height="100px" />
          ) : (
            <Text>{reasoning}</Text>
          )}
        </Box>
      </VStack>
    </Box>
  );
};

export default AnswerCard;
