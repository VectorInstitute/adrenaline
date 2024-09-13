import React, { useMemo } from 'react';
import { Box, Table, Thead, Tbody, Tr, Th, Td, Text, Divider, useColorModeValue } from '@chakra-ui/react';
import { QAPair } from '../types/patient';

interface QAPairsTableProps {
  qaPairs: QAPair[];
}

const QAPairsTable: React.FC<QAPairsTableProps> = ({ qaPairs }) => {
  const textColor = useColorModeValue('gray.800', 'gray.100');
  const tableBorderColor = useColorModeValue('gray.200', 'gray.600');
  const tableHoverBg = useColorModeValue('gray.100', 'gray.700');
  const tableHeaderBg = useColorModeValue('gray.100', 'gray.700');

  const memoizedQAPairs = useMemo(() => qaPairs, [qaPairs]);

  return (
    <Box overflowX="auto">
      <Table variant="simple" size="sm">
        <Thead>
          <Tr bg={tableHeaderBg}>
            <Th borderColor={tableBorderColor}>Question</Th>
            <Th borderColor={tableBorderColor}>Answer</Th>
          </Tr>
        </Thead>
        <Tbody>
          {memoizedQAPairs.map((qaPair, index) => (
            <React.Fragment key={`qa-pair-${index}`}>
              <Tr _hover={{ bg: tableHoverBg }} transition="background-color 0.2s">
                <Td borderColor={tableBorderColor}>
                  <Text fontSize="sm" color={textColor}>{qaPair.question}</Text>
                </Td>
                <Td borderColor={tableBorderColor}>
                  <Text fontSize="sm" color={textColor}>{qaPair.answer}</Text>
                </Td>
              </Tr>
              {index < memoizedQAPairs.length - 1 && (
                <Tr>
                  <Td colSpan={2} p={0}>
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

export default React.memo(QAPairsTable);
