import React, { useMemo } from 'react';
import { Box, Table, Thead, Tbody, Tr, Th, Td, Text, Tag, Badge, Tooltip, IconButton, Divider, useColorModeValue } from '@chakra-ui/react';
import { FaEye } from 'react-icons/fa';
import { ClinicalNote } from '../types/patient';

interface ClinicalNotesTableProps {
  notes: ClinicalNote[];
  handleNoteClick: (noteId: string) => void;
}

const ClinicalNotesTable: React.FC<ClinicalNotesTableProps> = ({ notes, handleNoteClick }) => {
  const textColor = useColorModeValue('gray.800', 'gray.100');
  const tableBorderColor = useColorModeValue('gray.200', 'gray.600');
  const tableHoverBg = useColorModeValue('gray.100', 'gray.700');
  const tableHeaderBg = useColorModeValue('gray.100', 'gray.700');

  const memoizedNotes = useMemo(() => notes, [notes]);

  return (
    <Box overflowX="auto">
      <Table variant="simple" size="sm">
        <Thead>
          <Tr bg={tableHeaderBg}>
            <Th borderColor={tableBorderColor}>Note ID</Th>
            <Th borderColor={tableBorderColor}>Encounter ID</Th>
            <Th borderColor={tableBorderColor}>Timestamp</Th>
            <Th borderColor={tableBorderColor}>Note Type</Th>
            <Th borderColor={tableBorderColor}>Text Preview</Th>
            <Th borderColor={tableBorderColor}>Action</Th>
          </Tr>
        </Thead>
        <Tbody>
          {memoizedNotes.map((note, index) => (
            <React.Fragment key={note.note_id}>
              <Tr
                _hover={{ bg: tableHoverBg }}
                transition="background-color 0.2s"
                cursor="pointer"
                onClick={() => handleNoteClick(note.note_id)}
              >
                <Td borderColor={tableBorderColor}>
                  <Tag colorScheme="blue" variant="solid">{note.note_id}</Tag>
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
                  <Badge colorScheme="green">{note.note_type}</Badge>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <Tooltip label={note.text} placement="top" hasArrow>
                    <Text fontSize="sm" color={textColor} isTruncated maxWidth="200px">
                      {note.text.substring(0, 50)}...
                    </Text>
                  </Tooltip>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <IconButton
                    aria-label="View note"
                    icon={<FaEye />}
                    size="sm"
                    colorScheme="blue"
                    variant="ghost"
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      handleNoteClick(note.note_id);
                    }}
                  />
                </Td>
              </Tr>
              {index < memoizedNotes.length - 1 && (
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
  );
};

export default React.memo(ClinicalNotesTable);
