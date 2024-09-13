import React, { useMemo, useCallback } from 'react';
import { Box, Text, Popover, PopoverTrigger, PopoverContent, PopoverBody, PopoverArrow, useColorModeValue, Table, Tbody, Tr, Td } from '@chakra-ui/react';

interface MetaAnnotation {
  value: string;
  confidence: number;
  name: string;
}

interface ICD10 {
  chapter: string;
  name: string;
}

interface Entity {
  pretty_name: string;
  cui: string;
  type_ids: string[];
  types: string[];
  source_value: string;
  detected_name: string;
  acc: number;
  context_similarity: number;
  start: number;
  end: number;
  icd10: ICD10[];
  ontologies: string[];
  snomed: string[];
  id: number;
  meta_anns: Record<string, MetaAnnotation>;
}

interface EntityVisualizationProps {
  text: string;
  entities: Entity[];
}

const EntityVisualization: React.FC<EntityVisualizationProps> = ({ text, entities }) => {
  const sortedEntities = useMemo(() => [...entities].sort((a, b) => a.start - b.start), [entities]);
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const getEntityColor = useCallback((entityTypes: string[]): string => {
    const baseColors = [
      'red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'teal', 'cyan', 'gray'
    ] as const;

    const hash = entityTypes.join('').split('').reduce((acc, char) => char.charCodeAt(0) + acc, 0);
    const colorIndex = hash % baseColors.length;
    const shade = (hash % 3 + 1) * 100; // This will give us shades 100, 200, or 300

    return `${baseColors[colorIndex]}.${shade}`;
  }, []);

  const renderText = useCallback(() => {
    let lastIndex = 0;
    const elements: JSX.Element[] = [];

    sortedEntities.forEach((entity, index) => {
      if (entity.start > lastIndex) {
        elements.push(
          <Text as="span" key={`text-${index}`}>
            {text.slice(lastIndex, entity.start)}
          </Text>
        );
      }

      elements.push(
        <Popover key={`entity-${index}`} trigger="hover" placement="top">
          <PopoverTrigger>
            <Text
              as="span"
              bg={getEntityColor(entity.types)}
              px={1}
              borderRadius="sm"
              cursor="pointer"
            >
              {text.slice(entity.start, entity.end)}
            </Text>
          </PopoverTrigger>
          <PopoverContent bg={bgColor} borderColor={borderColor}>
            <PopoverArrow />
            <PopoverBody>
              <Table size="sm">
                <Tbody>
                  <Tr>
                    <Td fontWeight="bold">Name:</Td>
                    <Td>{entity.pretty_name}</Td>
                  </Tr>
                  <Tr>
                    <Td fontWeight="bold">Types:</Td>
                    <Td>{entity.types.join(', ')}</Td>
                  </Tr>
                  <Tr>
                    <Td fontWeight="bold">CUI:</Td>
                    <Td>{entity.cui}</Td>
                  </Tr>
                  <Tr>
                    <Td fontWeight="bold">Accuracy:</Td>
                    <Td>{entity.acc.toFixed(2)}</Td>
                  </Tr>
                  {entity.icd10.length > 0 && (
                    <Tr>
                      <Td fontWeight="bold">ICD-10:</Td>
                      <Td>{entity.icd10.map(icd => `${icd.chapter}: ${icd.name}`).join(', ')}</Td>
                    </Tr>
                  )}
                </Tbody>
              </Table>
            </PopoverBody>
          </PopoverContent>
        </Popover>
      );

      lastIndex = entity.end;
    });

    if (lastIndex < text.length) {
      elements.push(
        <Text as="span" key="text-last">
          {text.slice(lastIndex)}
        </Text>
      );
    }

    return elements;
  }, [text, sortedEntities, getEntityColor, bgColor, borderColor]);

  return (
    <Box whiteSpace="pre-wrap">
      {renderText()}
    </Box>
  );
};

export default React.memo(EntityVisualization);
