import React from 'react';
import { Table, Thead, Tbody, Tr, Th, Td, Text, Tag, Badge, Tooltip, Box, useColorModeValue } from '@chakra-ui/react';
import { Event } from '../types/patient';

interface EventsTableProps {
  events: Event[];
}

const EventsTable: React.FC<EventsTableProps> = ({ events }) => {
  const textColor = useColorModeValue('gray.800', 'gray.100');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const getEventColor = (code: string) => {
    if (code.startsWith('LAB')) return 'blue';
    if (code.startsWith('DIAGNOSIS')) return 'red';
    if (code.startsWith('TRANSFER')) return 'green';
    if (code.startsWith('MEDICATION')) return 'purple';
    return 'gray';
  };

  return (
    <Box overflowX="auto">
      <Table variant="simple" size="sm">
        <Thead>
          <Tr>
            <Th borderColor={borderColor}>Timestamp</Th>
            <Th borderColor={borderColor}>Event Type</Th>
            <Th borderColor={borderColor}>Details</Th>
            <Th borderColor={borderColor}>Value</Th>
          </Tr>
        </Thead>
        <Tbody>
          {events.map((event, index) => (
            <Tr key={index}>
              <Td borderColor={borderColor}>
                <Text fontSize="sm" color={textColor}>{new Date(event.timestamp).toLocaleString()}</Text>
              </Td>
              <Td borderColor={borderColor}>
                <Tag colorScheme={getEventColor(event.code)}>{event.code.split('//')[0]}</Tag>
              </Td>
              <Td borderColor={borderColor}>
                <Tooltip label={event.code}>
                  <Text fontSize="sm" color={textColor} isTruncated maxWidth="200px">
                    {event.code}
                  </Text>
                </Tooltip>
              </Td>
              <Td borderColor={borderColor}>
                {event.numeric_value !== undefined ? (
                  <Badge colorScheme={getEventColor(event.code)}>{event.numeric_value}</Badge>
                ) : event.text_value ? (
                  <Tooltip label={event.text_value}>
                    <Text fontSize="sm" color={textColor} isTruncated maxWidth="200px">
                      {event.text_value}
                    </Text>
                  </Tooltip>
                ) : (
                  <Text fontSize="sm" color="gray.500">N/A</Text>
                )}
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default EventsTable;
