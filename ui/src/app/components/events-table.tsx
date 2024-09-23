import React, { useMemo } from 'react';
import { Table, Thead, Tbody, Tr, Th, Td, Text, Tag, Badge, Tooltip, Box, useColorModeValue, Flex, VStack } from '@chakra-ui/react';
import { Event } from '../types/patient';

interface EventsTableProps {
  events: Event[];
}

const EventsTable: React.FC<EventsTableProps> = ({ events }) => {
  const textColor = useColorModeValue('gray.800', 'gray.100');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const bgColor = useColorModeValue('white', 'gray.800');
  const hoverBgColor = useColorModeValue('gray.50', 'gray.700');

  const getEventColor = (eventType: string): string => {
    const colorMap: Record<string, string> = {
      LAB: 'blue',
      MEDICATION: 'purple',
      DIAGNOSIS: 'red',
      TRANSFER: 'green',
      PROCEDURE: 'orange',
      TRANSFER_TO: 'teal',
      TRANSFER_FROM: 'teal',
      HOSPITAL_ADMISSION: 'pink',
      HOSPITAL_DISCHARGE: 'pink',
    };
    return colorMap[eventType] || 'gray';
  };

  const formatEventDetails = useMemo(() => (code: string): JSX.Element => {
    const [eventType, ...details] = code.split('//');
    const color = getEventColor(eventType);

    return (
      <VStack align="start" spacing={2}>
        <Tag colorScheme={color} size="md" fontWeight="bold">{eventType}</Tag>
        <Flex flexWrap="wrap" gap={2}>
          {details.map((detail, index) => (
            <Badge key={index} colorScheme={color} px={2} py={1} borderRadius="full">
              {detail}
            </Badge>
          ))}
        </Flex>
      </VStack>
    );
  }, []);

  const renderValue = useMemo(() => (event: Event): JSX.Element => {
    const color = getEventColor(event.code.split('//')[0]);
    let value: number | string | null = null;
    let valueType: 'Numeric' | 'Text' | 'N/A' = 'N/A';

    if (typeof event.numeric_value === 'number') {
      value = event.numeric_value;
      valueType = 'Numeric';
    } else if (event.text_value) {
      value = event.text_value;
      valueType = 'Text';
    }

    return (
      <Tooltip label={valueType === 'N/A' ? 'Value is N/A' : `${valueType} value`} placement="top">
        <Badge
          colorScheme={color}
          fontSize="md"
          px={2}
          py={1}
          opacity={value === null ? 0.6 : 1}
        >
          {value !== null ? value : 'N/A'}
        </Badge>
      </Tooltip>
    );
  }, []);

  const memoizedEvents = useMemo(() => events, [events]);

  return (
    <Box overflowX="auto" borderWidth={1} borderRadius="lg" boxShadow="lg" bg={bgColor}>
      <Table variant="simple">
        <Thead>
          <Tr>
            <Th borderColor={borderColor} py={4}>Timestamp</Th>
            <Th borderColor={borderColor} py={4}>Event Details</Th>
            <Th borderColor={borderColor} py={4}>Value</Th>
          </Tr>
        </Thead>
        <Tbody>
          {memoizedEvents.map((event, index) => (
            <Tr key={index} _hover={{ bg: hoverBgColor }} transition="background-color 0.2s">
              <Td borderColor={borderColor} py={4}>
                <Text fontSize="sm" color={textColor} fontWeight="medium">
                  {new Date(event.timestamp).toLocaleString()}
                </Text>
              </Td>
              <Td borderColor={borderColor} py={4}>
                <Tooltip label={event.code} placement="top">
                  {formatEventDetails(event.code)}
                </Tooltip>
              </Td>
              <Td borderColor={borderColor} py={4}>
                {renderValue(event)}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default React.memo(EventsTable);
