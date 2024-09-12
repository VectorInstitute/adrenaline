import React from 'react';
import { Card, CardBody, VStack, Icon, Heading, Text, Skeleton, useColorModeValue } from '@chakra-ui/react';

interface StatCardProps {
  icon: React.ElementType;
  title: string;
  value: string | number;
  color: string;
  isLoading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ icon, title, value, color, isLoading = false }) => {
  const cardBgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Card bg={cardBgColor} p={6} borderRadius="xl" shadow="md" borderWidth={1} borderColor={borderColor}>
      <CardBody>
        <VStack spacing={4} align="center">
          <Icon as={icon} boxSize={10} color={`${color}.500`} />
          <Heading size="md" textAlign="center">{title}</Heading>
          {isLoading ? (
            <Skeleton height="24px" width="60px" />
          ) : (
            <Text fontSize="2xl" fontWeight="bold" color={`${color}.500`}>
              {value}
            </Text>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
};

export default StatCard;
